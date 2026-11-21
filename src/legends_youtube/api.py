"""Pure Python 3.11+ standard-library client for YouTube Data API v3, Analytics API v2, and OAuth 2.0 refresh."""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__

DEFAULT_DATA_BASE_URL = "https://www.googleapis.com/youtube/v3"
DEFAULT_UPLOAD_BASE_URL = "https://www.googleapis.com/upload/youtube/v3"
DEFAULT_ANALYTICS_BASE_URL = "https://youtubeanalytics.googleapis.com/v2"
DEFAULT_TOKEN_URL = "https://oauth2.googleapis.com/token"
ALLOWED_API_HOSTS = {"www.googleapis.com", "youtubeanalytics.googleapis.com", "oauth2.googleapis.com"}

SCOPE_READONLY = "https://www.googleapis.com/auth/youtube.readonly"
SCOPE_FORCE_SSL = "https://www.googleapis.com/auth/youtube.force-ssl"
SCOPE_UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
SCOPE_ANALYTICS_READONLY = "https://www.googleapis.com/auth/yt-analytics.readonly"
SCOPE_ANALYTICS_MONETARY_READONLY = "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"

MAX_FILE_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 10 * 1024 * 1024

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
PLAYLIST_ID_RE = re.compile(r"^(?:PL|UU|FL|LL|RD|WL|OLAK5uy_)[A-Za-z0-9_-]{10,80}$")

_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")

_SECRET_SCRUB_RE = re.compile(
    r"(?:\bya29\.[A-Za-z0-9._-]{16,}|\b1//[A-Za-z0-9._-]{20,}|\b1/[A-Za-z0-9._-]{20,}|\bAIza[0-9A-Za-z_-]{20,}|\bGOCSPX-[A-Za-z0-9_-]{16,})"
)
_BEARER_SCRUB_RE = re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]{10,}")
_KV_SECRET_SCRUB_RE = re.compile(
    r"(?i)(\b(?:access_token|refresh_token|client_secret|api_key|key)\s*[=:]\s*['\"]?)([^'\"&\s,;}{]{8,})"
)


class YouTubeError(RuntimeError):
    """Structured error from YouTube API or local safety validation."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        reason: str | None = None,
        domain: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.domain = domain


def scrub_secrets(text: str) -> str:
    """Redact Google OAuth access/refresh tokens, client secrets, Bearer tokens, and API keys from logs or errors."""
    out = _SECRET_SCRUB_RE.sub("[REDACTED_GOOGLE_SECRET]", text or "")
    out = _BEARER_SCRUB_RE.sub(r"\1[REDACTED_GOOGLE_SECRET]", out)
    out = _KV_SECRET_SCRUB_RE.sub(r"\1[REDACTED_GOOGLE_SECRET]", out)
    return out


def validate_video_id(value: str, *, field_name: str = "video_id") -> str:
    """Validate that a YouTube video ID is an exact 11-character base64url token (prevents CWE-22 path traversal)."""
    cleaned = (value or "").strip()
    if not VIDEO_ID_RE.fullmatch(cleaned):
        raise YouTubeError(f"Invalid YouTube {field_name} format: {scrub_secrets(cleaned)!r}")
    return cleaned


def validate_channel_id(value: str, *, field_name: str = "channel_id") -> str:
    """Validate that a YouTube channel ID starts with UC followed by 22 base64url characters."""
    cleaned = (value or "").strip()
    if not CHANNEL_ID_RE.fullmatch(cleaned):
        raise YouTubeError(f"Invalid YouTube {field_name} format (expected UC + 22 chars): {scrub_secrets(cleaned)!r}")
    return cleaned


def validate_playlist_id(value: str, *, field_name: str = "playlist_id") -> str:
    """Validate a YouTube playlist ID (PL..., UU..., etc.)."""
    cleaned = (value or "").strip()
    if not PLAYLIST_ID_RE.fullmatch(cleaned):
        raise YouTubeError(f"Invalid YouTube {field_name} format: {scrub_secrets(cleaned)!r}")
    return cleaned


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse automatic HTTP redirects so Authorization headers or SSRF probes never follow 3xx responses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirects are disabled ({code})", headers, fp)

    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    def http_error_303(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    def http_error_307(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    def http_error_308(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


def build_safe_opener() -> urllib.request.OpenerDirector:
    """Build a urllib opener that refuses automatic HTTP redirects."""
    return urllib.request.build_opener(_NoRedirectHandler())


def _check_public_ip(ip_str: str) -> str:
    addr = ipaddress.ip_address(ip_str)
    check_addr = addr.ipv4_mapped if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None else addr
    if (
        not check_addr.is_global
        or check_addr.is_private
        or check_addr.is_loopback
        or check_addr.is_link_local
        or check_addr.is_multicast
        or check_addr.is_reserved
        or check_addr.is_unspecified
        or (isinstance(check_addr, ipaddress.IPv4Address) and check_addr in _CGNAT_NETWORK)
    ):
        raise YouTubeError(f"Refusing non-public IP address target: {ip_str}")
    return str(addr)


def resolve_public_https_ips(hostname: str, *, port: int = 443, resolve_dns: bool = True) -> tuple[str, list[str]]:
    """Validate a public HTTPS hostname/IP and return (normalized_host, validated_public_ips)."""
    raw_host = (hostname or "").strip()
    if raw_host.startswith("[") and raw_host.endswith("]"):
        raw_host = raw_host[1:-1]
    host = raw_host.lower().rstrip(".")
    if not host or any(c in host for c in ("/", "@", " ", "\t", "\r", "\n", "\x00")):
        raise YouTubeError(f"Invalid target hostname: {hostname!r}")

    try:
        checked_ip = _check_public_ip(host)
        return host, [checked_ip]
    except ValueError:
        pass

    if ":" in host:
        raise YouTubeError(f"Invalid target hostname: {hostname!r}")
    if host in ("localhost", "localhost.localdomain") or host.endswith(
        (".local", ".internal", ".localhost", ".lan", ".home.arpa", ".corp", ".home")
    ):
        raise YouTubeError(f"Refusing non-public or local hostname: {host}")

    resolved_ips: list[str] = []
    if resolve_dns:
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise YouTubeError(f"DNS resolution failed for {host}: {exc}") from exc
        if not infos:
            raise YouTubeError(f"DNS resolution returned no addresses for {host}")
        for family, _, _, _, sockaddr in infos:
            if family in (socket.AF_INET, socket.AF_INET6) and sockaddr:
                ip_val = _check_public_ip(str(sockaddr[0]))
                if ip_val not in resolved_ips:
                    resolved_ips.append(ip_val)
        if not resolved_ips:
            raise YouTubeError(f"DNS resolution returned no usable addresses for {host}")
    return host, resolved_ips


def validate_public_https_host(hostname: str, *, resolve_dns: bool = True) -> str:
    """Reject loopback, link-local, RFC1918 private, CGNAT/Tailscale, multicast, and internal hostnames/IPs (CWE-918 SSRF defense)."""
    host, _ = resolve_public_https_ips(hostname, resolve_dns=resolve_dns)
    return host


_MACOS_SYSTEM_SYMLINKS = {Path("/var"), Path("/tmp"), Path("/etc")}
_WINDOWS_CFA_DIRS = ("Desktop", "Documents", "Pictures", "Videos", "Music", "OneDrive", "Favorites")


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junc = getattr(path, "is_junction", None)
    if callable(is_junc):
        try:
            return bool(is_junc())
        except OSError:
            return False
    return False


def _reject_symlink_chain(path: Path) -> None:
    """Refuse symlinks or NTFS junctions on the target path or any non-system parent directory (CWE-59)."""
    raw = Path(path).expanduser()
    abs_path = Path(os.path.abspath(os.fspath(raw)))
    for candidate in (raw, abs_path):
        if _is_link_or_junction(candidate):
            raise YouTubeError(f"Refusing to operate on symlink path: {path}")
    for parent in abs_path.parents:
        if parent in _MACOS_SYSTEM_SYMLINKS:
            continue
        if _is_link_or_junction(parent):
            raise YouTubeError(f"Refusing to traverse symlinked directory: {parent}")


def _reject_protected_write_target(target: Path) -> None:
    """Refuse writing inside Windows system roots or Controlled Folder Access user directories."""
    if os.name != "nt":
        return
    for env_key in ("SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        val = os.environ.get(env_key)
        if val:
            try:
                sys_root = Path(val).resolve()
                if target == sys_root or target.is_relative_to(sys_root):
                    raise YouTubeError(f"Refusing to write inside protected system directory: {target}")
            except OSError:
                pass
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        try:
            user_root = Path(user_profile).resolve()
            if target.parent == user_root:
                raise YouTubeError(f"Refusing to write directly into user profile root: {target}")
            for folder in _WINDOWS_CFA_DIRS:
                for cfa_dir in (user_root / folder, user_root / "OneDrive" / folder):
                    if target == cfa_dir or target.is_relative_to(cfa_dir):
                        raise YouTubeError(
                            f"Refusing to write inside Controlled Folder Access protected directory: {target}"
                        )
        except OSError:
            pass


def safe_read_text_file(path: str | Path, *, max_bytes: int = MAX_FILE_BYTES, label: str = "file") -> tuple[Path, str]:
    """Read a regular UTF-8 file after verifying it is not a symlink and does not exceed max_bytes."""
    raw_path = Path(path).expanduser()
    _reject_symlink_chain(raw_path)
    target = raw_path.resolve()
    if not target.is_file() or _is_link_or_junction(target):
        raise YouTubeError(f"Requested {label} does not exist or is not a regular file: {target}")
    size = target.stat().st_size
    if size > max_bytes:
        raise YouTubeError(f"Requested {label} exceeds {max_bytes} bytes ({size} bytes): {target}")
    return target, target.read_text(encoding="utf-8", errors="replace")


def safe_read_json_file(path: str | Path, *, max_bytes: int = MAX_FILE_BYTES, label: str = "JSON file") -> tuple[Path, Any, str]:
    """Read and parse a regular UTF-8 JSON file and return (resolved_path, parsed_data, sha256_hex)."""
    raw_path = Path(path).expanduser()
    _reject_symlink_chain(raw_path)
    target = raw_path.resolve()
    if not target.is_file() or _is_link_or_junction(target):
        raise YouTubeError(f"Requested {label} does not exist or is not a regular file: {target}")
    size = target.stat().st_size
    if size > max_bytes:
        raise YouTubeError(f"Requested {label} exceeds {max_bytes} bytes ({size} bytes): {target}")
    raw = target.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        parsed = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise YouTubeError(f"Invalid UTF-8 JSON in {label} ({target}): {exc}") from exc
    return target, parsed, digest


def safe_write_text_file(path_str: str | Path, content: str, *, overwrite: bool = False) -> str:
    """Write a single UTF-8 report file safely without following symlinks or silently overwriting existing files."""
    raw_path = Path(path_str).expanduser()
    _reject_symlink_chain(raw_path)
    target = raw_path.resolve()
    _reject_protected_write_target(target)
    if target.exists() and _is_link_or_junction(target):
        raise YouTubeError(f"Refusing to write to symlink path: {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_chain(raw_path)
        if target.exists() and _is_link_or_junction(target):
            raise YouTubeError(f"Refusing to write to symlink path: {target}")
        if overwrite:
            tmp_path = target.parent / f".{target.name}.{os.getpid()}.tmp"
            if tmp_path.exists():
                tmp_path.unlink()
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(str(tmp_path), flags, 0o600)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(content)
                os.replace(tmp_path, target)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                fd = os.open(str(target), flags, 0o600)
            except FileExistsError:
                raise YouTubeError(f"Output file already exists (pass --overwrite to replace): {target}") from None
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
    except YouTubeError:
        raise
    except OSError as exc:
        raise YouTubeError(f"Failed to write output file {target}: {exc}") from exc
    return str(target)


def parse_dotenv_file(dotenv_path: str | Path) -> dict[str, str]:
    """Parse a user-supplied .env file without mutating os.environ."""
    _, text = safe_read_text_file(dotenv_path, label=".env file")
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
            val = val[1:-1]
        else:
            for comment_sep in (" #", "\t#"):
                if comment_sep in val:
                    val = val.split(comment_sep, 1)[0].rstrip()
        if key:
            values[key] = val
    return values


def resolve_credentials(
    *,
    dotenv_path: str | Path | None = None,
    token_file: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve YouTube API credentials from explicit env vars, optional --dotenv, or an explicit --token-file.

    Never scans browser profiles or system credential stores.
    """
    merged: dict[str, str] = dict(os.environ if env is None else env)
    if dotenv_path:
        dotenv_vals = parse_dotenv_file(dotenv_path)
        for k, v in dotenv_vals.items():
            merged.setdefault(k, v)

    access_token = (merged.get("YOUTUBE_ACCESS_TOKEN") or "").strip()
    refresh_token = (merged.get("YOUTUBE_REFRESH_TOKEN") or "").strip()
    client_id = (merged.get("YOUTUBE_CLIENT_ID") or merged.get("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (merged.get("YOUTUBE_CLIENT_SECRET") or merged.get("GOOGLE_CLIENT_SECRET") or "").strip()
    api_key = (merged.get("YOUTUBE_API_KEY") or "").strip()
    channel_id = (merged.get("YOUTUBE_CHANNEL_ID") or "").strip()
    scopes: list[str] = []

    resolved_token_file = token_file or merged.get("YOUTUBE_TOKEN_FILE") or ""
    if resolved_token_file:
        _, token_data, _ = safe_read_json_file(resolved_token_file, label="OAuth token JSON")
        if isinstance(token_data, dict):
            access_token = access_token or str(token_data.get("token") or token_data.get("access_token") or "").strip()
            refresh_token = refresh_token or str(token_data.get("refresh_token") or "").strip()
            client_id = client_id or str(token_data.get("client_id") or "").strip()
            client_secret = client_secret or str(token_data.get("client_secret") or "").strip()
            raw_scopes = token_data.get("scopes") or token_data.get("scope") or []
            if isinstance(raw_scopes, str):
                scopes = [s.strip() for s in raw_scopes.split() if s.strip()]
            elif isinstance(raw_scopes, list):
                scopes = [str(s).strip() for s in raw_scopes if str(s).strip()]

    has_oauth_refresh = bool(refresh_token and client_id and client_secret)
    has_oauth_token = bool(access_token or has_oauth_refresh)
    write_capable = any(
        s in (SCOPE_FORCE_SSL, SCOPE_UPLOAD, "https://www.googleapis.com/auth/youtube") for s in scopes
    ) or (has_oauth_token and not scopes)
    upload_capable = any(
        s in (SCOPE_UPLOAD, SCOPE_FORCE_SSL, "https://www.googleapis.com/auth/youtube") for s in scopes
    ) or (has_oauth_token and not scopes)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "api_key": api_key,
        "channel_id": channel_id,
        "scopes": scopes,
        "has_oauth": has_oauth_token,
        "has_oauth_refresh": has_oauth_refresh,
        "has_api_key": bool(api_key),
        "write_scope_granted": write_capable if scopes else None,
        "upload_scope_granted": upload_capable if scopes else None,
    }


def redact_credential_summary(creds: dict[str, Any]) -> dict[str, Any]:
    """Return a safe, secret-free diagnostic summary of resolved credential state."""
    return {
        "has_oauth": bool(creds.get("has_oauth")),
        "has_oauth_refresh": bool(creds.get("has_oauth_refresh")),
        "has_access_token": bool(creds.get("access_token")),
        "has_api_key": bool(creds.get("has_api_key")),
        "channel_id": creds.get("channel_id") or None,
        "scopes": list(creds.get("scopes") or []),
        "write_scope_granted": creds.get("write_scope_granted"),
        "upload_scope_granted": creds.get("upload_scope_granted"),
    }


class YouTubeClient:
    """Zero-dependency HTTP client for YouTube Data API v3 and YouTube Analytics API v2."""

    def __init__(
        self,
        *,
        access_token: str = "",
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        api_key: str = "",
        data_base_url: str = DEFAULT_DATA_BASE_URL,
        upload_base_url: str = DEFAULT_UPLOAD_BASE_URL,
        analytics_base_url: str = DEFAULT_ANALYTICS_BASE_URL,
        token_url: str = DEFAULT_TOKEN_URL,
        timeout: float = 30.0,
    ) -> None:
        self._access_token = (access_token or "").strip()
        self._refresh_token = (refresh_token or "").strip()
        self._client_id = (client_id or "").strip()
        self._client_secret = (client_secret or "").strip()
        self._api_key = (api_key or "").strip()
        self.data_base_url = data_base_url.rstrip("/")
        self.upload_base_url = upload_base_url.rstrip("/")
        self.analytics_base_url = analytics_base_url.rstrip("/")
        self.token_url = token_url
        self.timeout = timeout
        self._opener = build_safe_opener()

    @property
    def access_token(self) -> str:
        return self._access_token

    @classmethod
    def from_credentials(cls, creds: dict[str, Any], **kwargs: Any) -> "YouTubeClient":
        return cls(
            access_token=creds.get("access_token", ""),
            refresh_token=creds.get("refresh_token", ""),
            client_id=creds.get("client_id", ""),
            client_secret=creds.get("client_secret", ""),
            api_key=creds.get("api_key", ""),
            **kwargs,
        )

    def _validate_api_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise YouTubeError(f"YouTube API URL must use https://: {scrub_secrets(url)}")
        if parsed.username or parsed.password:
            raise YouTubeError("YouTube API URL must not contain embedded credentials.")
        try:
            port = parsed.port
        except ValueError:
            raise YouTubeError("Invalid port in YouTube API URL.") from None
        if port not in (None, 443):
            raise YouTubeError(f"Refusing non-443 port in YouTube API URL: {port}")
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_API_HOSTS:
            raise YouTubeError(f"Refusing non-Google API host: {host!r}")

    def refresh_access_token(self) -> str:
        """Exchange refresh_token for a fresh OAuth 2.0 access_token."""
        if not (self._refresh_token and self._client_id and self._client_secret):
            raise YouTubeError(
                "OAuth token refresh requires YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, and YOUTUBE_CLIENT_SECRET."
            )
        self._validate_api_url(self.token_url)
        body = urllib.parse.urlencode(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.token_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": f"legends-youtube/{__version__}",
            },
        )
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise YouTubeError(f"OAuth token response exceeded {MAX_RESPONSE_BYTES} bytes.")
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read(65536).decode("utf-8", errors="replace")
            except Exception:
                pass
            hint = ""
            if "invalid_grant" in err_body:
                hint = (
                    " (Hint: if your Google Cloud OAuth consent screen is in 'Testing' mode, "
                    "Google expires refresh tokens after 7 days; switch publishing status to 'In production' or re-authorize.)"
                )
            raise YouTubeError(
                f"OAuth token refresh failed ({exc.code}): {scrub_secrets(err_body or str(exc))}{hint}",
                status=exc.code,
                reason="oauthRefreshFailed",
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            raise YouTubeError(f"Network error during OAuth refresh: {scrub_secrets(str(exc))}") from None

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise YouTubeError(f"Invalid JSON response from OAuth token endpoint: {exc}") from None
        if not isinstance(data, dict):
            raise YouTubeError("OAuth token endpoint did not return a JSON object.")
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise YouTubeError("OAuth token endpoint returned no access_token.")
        self._access_token = token
        return token

    def ensure_access_token(self) -> str:
        """Return an OAuth access token, refreshing if needed."""
        if self._access_token:
            return self._access_token
        if self._refresh_token and self._client_id and self._client_secret:
            return self.refresh_access_token()
        raise YouTubeError(
            "Missing OAuth credentials. Set YOUTUBE_ACCESS_TOKEN or (YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET)."
        )

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_oauth: bool = False,
    ) -> dict[str, Any]:
        """Execute an authenticated JSON request against YouTube Data API v3 or Analytics API v2."""
        query = dict(params or {})
        req_headers = {
            "Accept": "application/json",
            "User-Agent": f"legends-youtube/{__version__}",
        }
        if headers:
            req_headers.update(headers)

        if require_oauth or self._access_token or (self._refresh_token and self._client_id and self._client_secret):
            token = self.ensure_access_token()
            req_headers["Authorization"] = f"Bearer {token}"
        elif self._api_key:
            query["key"] = self._api_key
        else:
            raise YouTubeError(
                "No YouTube credentials configured. Set YOUTUBE_API_KEY (read-only public) or OAuth env vars."
            )

        full_url = url
        if query:
            clean_query = {k: str(v) for k, v in query.items() if v is not None and v != ""}
            sep = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{sep}{urllib.parse.urlencode(clean_query)}"

        self._validate_api_url(full_url)
        payload: bytes | None = None
        if json_body is not None:
            payload = json.dumps(json_body).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"

        req = urllib.request.Request(full_url, data=payload, method=method.upper(), headers=req_headers)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise YouTubeError(f"YouTube API response exceeded {MAX_RESPONSE_BYTES} bytes.")
        except urllib.error.HTTPError as exc:
            if (
                exc.code == 401
                and self._refresh_token
                and self._client_id
                and self._client_secret
                and (not headers or not headers.get("_retried_oauth_refresh"))
            ):
                fresh_token = self.refresh_access_token()
                retry_headers = dict(headers or {})
                retry_headers["_retried_oauth_refresh"] = "1"
                req_headers["Authorization"] = f"Bearer {fresh_token}"
                req_headers.pop("_retried_oauth_refresh", None)
                retry_req = urllib.request.Request(full_url, data=payload, method=method.upper(), headers=req_headers)
                try:
                    with self._opener.open(retry_req, timeout=self.timeout) as resp2:
                        raw = resp2.read(MAX_RESPONSE_BYTES + 1)
                        if len(raw) > MAX_RESPONSE_BYTES:
                            raise YouTubeError(f"YouTube API response exceeded {MAX_RESPONSE_BYTES} bytes.")
                except urllib.error.HTTPError as retry_exc:
                    exc = retry_exc
                except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as retry_url_exc:
                    raise YouTubeError(f"YouTube API network error: {scrub_secrets(str(retry_url_exc))}") from None
                else:
                    if not raw:
                        return {}
                    try:
                        parsed = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as parse_exc:
                        raise YouTubeError(f"Invalid JSON response from YouTube API: {parse_exc}") from None
                    return parsed if isinstance(parsed, dict) else {"items": parsed}
            err_text = ""
            try:
                err_text = exc.read(131072).decode("utf-8", errors="replace")
            except Exception:
                pass
            reason = None
            domain = None
            msg = f"YouTube API HTTP {exc.code}"
            try:
                err_json = json.loads(err_text)
                err_obj = err_json.get("error", {}) if isinstance(err_json, dict) else {}
                if isinstance(err_obj, dict):
                    msg = str(err_obj.get("message") or msg)
                    errors_list = err_obj.get("errors") or []
                    if isinstance(errors_list, list) and errors_list and isinstance(errors_list[0], dict):
                        reason = str(errors_list[0].get("reason") or "") or None
                        domain = str(errors_list[0].get("domain") or "") or None
            except Exception:
                if err_text:
                    msg = f"{msg}: {err_text[:300]}"
            raise YouTubeError(scrub_secrets(msg), status=exc.code, reason=reason, domain=domain) from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            raise YouTubeError(f"YouTube API network error: {scrub_secrets(str(exc))}") from None

        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise YouTubeError(f"Invalid JSON response from YouTube API: {exc}") from None
        return parsed if isinstance(parsed, dict) else {"items": parsed}

    def get_channel(self, *, channel_id: str | None = None, mine: bool = False) -> dict[str, Any]:
        """Fetch a single YouTube channel resource (1 quota unit)."""
        params: dict[str, Any] = {
            "part": "id,snippet,statistics,contentDetails,status,brandingSettings",
            "maxResults": 1,
        }
        if mine:
            params["mine"] = "true"
        elif channel_id:
            params["id"] = validate_channel_id(channel_id)
        else:
            raise YouTubeError("Specify channel_id or mine=True for get_channel().")
        resp = self.request_json(
            "GET",
            f"{self.data_base_url}/channels",
            params=params,
            require_oauth=mine,
        )
        items = resp.get("items") or []
        if not items or not isinstance(items[0], dict):
            raise YouTubeError("No matching YouTube channel returned by channels.list.")
        return items[0]

    def list_playlist_video_ids(self, playlist_id: str, *, max_items: int = 500) -> list[str]:
        """Page through a playlist (e.g., channel uploads UU...) at 1 quota unit per 50 items."""
        clean_pid = validate_playlist_id(playlist_id)
        video_ids: list[str] = []
        page_token: str | None = None
        while len(video_ids) < max_items:
            batch_size = min(50, max_items - len(video_ids))
            params: dict[str, Any] = {
                "part": "contentDetails",
                "playlistId": clean_pid,
                "maxResults": batch_size,
            }
            if page_token:
                params["pageToken"] = page_token
            resp = self.request_json("GET", f"{self.data_base_url}/playlistItems", params=params)
            for item in resp.get("items") or []:
                if isinstance(item, dict):
                    vid = (item.get("contentDetails") or {}).get("videoId")
                    if isinstance(vid, str) and VIDEO_ID_RE.fullmatch(vid):
                        video_ids.append(vid)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return video_ids

    def list_videos_by_ids(
        self,
        video_ids: list[str],
        *,
        part: str = "id,snippet,status,contentDetails,statistics",
    ) -> list[dict[str, Any]]:
        """Batch-fetch video resources in 50-ID chunks (1 quota unit per 50 videos)."""
        cleaned = [validate_video_id(v) for v in video_ids]
        results: list[dict[str, Any]] = []
        for start in range(0, len(cleaned), 50):
            chunk = cleaned[start : start + 50]
            resp = self.request_json(
                "GET",
                f"{self.data_base_url}/videos",
                params={"part": part, "id": ",".join(chunk), "maxResults": len(chunk)},
            )
            for item in resp.get("items") or []:
                if isinstance(item, dict):
                    results.append(item)
        return results

    def update_video_snippet(
        self,
        *,
        video_id: str,
        snippet: dict[str, Any],
        etag: str,
    ) -> dict[str, Any]:
        """Update a video's snippet with If-Match ETag optimistic concurrency (50 quota units)."""
        clean_vid = validate_video_id(video_id)
        if not etag or not etag.strip():
            raise YouTubeError(f"Refusing videos.update without preflight ETag for {clean_vid}.")
        body = {
            "id": clean_vid,
            "snippet": snippet,
        }
        return self.request_json(
            "PUT",
            f"{self.data_base_url}/videos",
            params={"part": "snippet"},
            json_body=body,
            headers={"If-Match": etag.strip()},
            require_oauth=True,
        )

    def query_analytics_report(
        self,
        *,
        start_date: str,
        end_date: str,
        metrics: str = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost",
        dimensions: str = "video",
        max_results: int = 200,
        sort: str = "-views",
        ids: str = "channel==MINE",
        filters: str = "",
    ) -> dict[str, Any]:
        """Query YouTube Analytics API v2 reports endpoint."""
        params: dict[str, Any] = {
            "ids": ids,
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics,
            "dimensions": dimensions,
            "maxResults": max_results,
            "sort": sort,
        }
        if filters:
            params["filters"] = filters
        return self.request_json(
            "GET",
            f"{self.analytics_base_url}/reports",
            params=params,
            require_oauth=True,
        )
