"""Comprehensive unit tests for legends-youtube."""
from __future__ import annotations

import email.message
import http.client
import io
import json
import os
import socket
import struct
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

from legends_youtube.analytics import (
    channel_health,
    normalize_records,
    packaging_audit,
    parse_analytics_api_response,
    render_scorecard_markdown,
    score_video_idea,
)
from legends_youtube.api import (
     YouTubeClient,
    YouTubeError,
    _NoRedirectHandler,
    _reject_symlink_chain,
    parse_dotenv_file,
    redact_credential_summary,
    resolve_credentials,
    safe_write_text_file,
    scrub_secrets,
    validate_channel_id,
    validate_playlist_id,
    validate_public_https_host,
    validate_video_id,
)
from legends_youtube.cli import main as cli_main
from legends_youtube.engagement import (
    audit_playlists,
    audit_shorts_funnel,
    normalize_comment_thread_item,
    triage_comments,
)
from legends_youtube.intelligence import (
    _safe_parse_xml_bytes,
    compile_transcript_package,
    correlate_retention_with_transcript,
    load_transcript_segments,
    scout_channel_outliers,
)
from legends_youtube.inventory import (
    _extract_balanced_json,
    extract_chapter_lines,
    extract_urls,
    normalize_api_video_item,
    parse_iso8601_duration,
)
from legends_youtube.metadata import (
    build_merged_snippet,
    canonical_plan_sha256,
    execute_metadata_plan,
    generate_link_migration_plan,
    legends_lowercase_title,
    preview_metadata_plan,
    validate_metadata_plan,
)
from legends_youtube.quota import inventory_quota_cost, plan_quota_budget
from legends_youtube.resources import resolve as resolve_resources
from legends_youtube.studio_lint import (
    audit_description_links,
    lint_chapters,
    lint_house_style,
    lint_studio_quizzes,
    probe_public_https_url,
    validate_related_video_guard,
)
from legends_youtube.upload import (
    _video_mime_type,
    execute_private_draft_upload,
    freeze_draft_plan,
    inspect_thumbnail,
    verify_frozen_draft_plan,
)


def _make_minimal_png(width: int = 1280, height: int = 720) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", 0)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", 0)
    return b"\x89PNG\r\n\x1a\n" + ihdr_chunk + iend_chunk


class FakeYouTubeClient(YouTubeClient):
    """In-memory fake YouTubeClient for testing preflight, ETag concurrency, and readback verification."""

    def __init__(self, videos: dict[str, dict[str, Any]]) -> None:
        super().__init__(access_token="fake_token")
        self.store = json.loads(json.dumps(videos))
        self.update_calls: list[dict[str, Any]] = []

    def list_videos_by_ids(
        self,
        video_ids: list[str],
        *,
        part: str = "id,snippet,status,contentDetails,statistics",
    ) -> list[dict[str, Any]]:
        return [json.loads(json.dumps(self.store[vid])) for vid in video_ids if vid in self.store]

    def update_video_snippet(self, *, video_id: str, snippet: dict[str, Any], etag: str) -> dict[str, Any]:
        if video_id not in self.store:
            raise YouTubeError(f"Not found: {video_id}", status=404)
        current = self.store[video_id]
        if current.get("etag") != etag:
            raise YouTubeError("ETag precondition failed", status=412)
        self.update_calls.append({"video_id": video_id, "snippet": dict(snippet), "etag": etag})
        current["snippet"] = dict(snippet)
        current["etag"] = f"{etag}_v2"
        return json.loads(json.dumps(current))


class ApiAndSecurityTests(unittest.TestCase):
    def test_secret_scrubbing(self) -> None:
        tok_ya29 = "ya29." + "a0AfH6SMBx1234567890abcdef"
        tok_aiza = "AIza" + "SyD1234567890abcdefghijklmnopqrstuv"
        tok_gocspx = "GOCSPX-" + "1234567890abcdefghij"
        tok_ref1 = "1/" + "fFAGRNJru1FTz70BzhT3Zg0123456789"
        tok_ref2 = "1//" + "0fFAGRNJru1FTz70BzhT3Zg0123456789"
        raw = (
            f"Bearer {tok_ya29} and key {tok_aiza} "
            f"and {tok_gocspx} and {tok_ref1} and {tok_ref2} "
            "and Authorization: Bearer custom_oauth_token_abc12345 "
            "and client_secret=my_super_secret_val_999"
        )
        scrubbed = scrub_secrets(raw)
        self.assertNotIn("ya29.", scrubbed)
        self.assertNotIn("AIza", scrubbed)
        self.assertNotIn("GOCSPX-", scrubbed)
        self.assertNotIn("fFAGRNJru1FTz70BzhT3Zg", scrubbed)
        self.assertNotIn("custom_oauth_token_abc12345", scrubbed)
        self.assertNotIn("my_super_secret_val_999", scrubbed)
        self.assertIn("[REDACTED_GOOGLE_SECRET]", scrubbed)

    def test_id_validators(self) -> None:
        self.assertEqual(validate_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(validate_channel_id("UC_x5XG1OV2P6uZZ5FSM9Ttw"), "UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual(validate_playlist_id("UU_x5XG1OV2P6uZZ5FSM9Ttw"), "UU_x5XG1OV2P6uZZ5FSM9Ttw")
        with self.assertRaises(YouTubeError):
            validate_video_id("../etc/passwd")
        with self.assertRaises(YouTubeError):
            validate_channel_id("bad_channel")

    def test_ssrf_guard_rejects_local_private_cgnat_mapped_and_dns_failures(self) -> None:
        for blocked in (
            "localhost",
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.1",
            "169.254.169.254",
            "100.64.0.1",
            "100.100.100.100",
            "::ffff:127.0.0.1",
            "[::ffff:100.64.0.1]",
            "app.internal",
        ):
            with self.assertRaises(YouTubeError, msg=f"Expected {blocked} to be rejected"):
                validate_public_https_host(blocked, resolve_dns=False)
        self.assertEqual(validate_public_https_host("cto-legends.com", resolve_dns=False), "cto-legends.com")

        # DNS resolution returning CGNAT or IPv4-mapped loopback must fail closed
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("100.64.0.5", 443))]):
            with self.assertRaises(YouTubeError):
                validate_public_https_host("rebind.example.com", resolve_dns=True)

        with patch(
            "socket.getaddrinfo",
            return_value=[(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:127.0.0.1", 443, 0, 0))],
        ):
            with self.assertRaises(YouTubeError):
                validate_public_https_host("mapped.example.com", resolve_dns=True)

        with patch("socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
            with self.assertRaises(YouTubeError):
                validate_public_https_host("unresolvable.example.com", resolve_dns=True)

    def test_probe_public_https_url_rejects_credentials_and_non_443_ports(self) -> None:
        res_cred = probe_public_https_url("https://user:pass@example.com/path")
        self.assertFalse(res_cred["ok"])
        self.assertIn("credentials", res_cred["note"])

        res_port = probe_public_https_url("https://example.com:8443/path")
        self.assertFalse(res_port["ok"])
        self.assertIn("8443", res_port["note"])

        # Verify pinned IP is passed to socket.create_connection (preventing DNS rebinding)
        fake_resp = unittest.mock.MagicMock()
        fake_resp.status = 200
        with (
            patch("legends_youtube.studio_lint.resolve_public_https_ips", return_value=("example.com", ["93.184.216.34"])),
            patch("legends_youtube.studio_lint.socket.create_connection") as mock_conn,
            patch("legends_youtube.studio_lint.ssl.create_default_context") as mock_ssl,
            patch("legends_youtube.studio_lint.http.client.HTTPConnection") as mock_http,
        ):
            mock_http.return_value.getresponse.return_value = fake_resp
            res_ok = probe_public_https_url("https://example.com/docs?x=1")
            self.assertTrue(res_ok["ok"])
            self.assertEqual(res_ok["status"], 200)
            mock_conn.assert_called_once_with(("93.184.216.34", 443), timeout=10.0)
            mock_ssl.return_value.wrap_socket.assert_called_once_with(
                mock_conn.return_value,
                server_hostname="example.com",
            )

    def test_no_redirect_handler_refuses_301_302_307_308(self) -> None:
        handler = _NoRedirectHandler()
        req = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos")
        hdrs = email.message.Message()
        for code, method in ((301, handler.http_error_301), (302, handler.http_error_302), (307, handler.http_error_307), (308, handler.http_error_308)):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                method(req, None, code, "Redirect", hdrs)
            self.assertEqual(ctx.exception.code, code)

    def test_dotenv_inline_comments_and_upload_scope_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "YOUTUBE_CHANNEL_ID=UC_x5XG1OV2P6uZZ5FSM9Ttw # inline comment\n"
                'YOUTUBE_CLIENT_ID="quoted#kept"\n'
                "export YOUTUBE_ACCESS_TOKEN=tok_123\t# tab comment\n",
                encoding="utf-8",
            )
            parsed = parse_dotenv_file(env_file)
            self.assertEqual(parsed["YOUTUBE_CHANNEL_ID"], "UC_x5XG1OV2P6uZZ5FSM9Ttw")
            self.assertEqual(parsed["YOUTUBE_CLIENT_ID"], "quoted#kept")
            self.assertEqual(parsed["YOUTUBE_ACCESS_TOKEN"], "tok_123")

            token_file = Path(tmp) / "token.json"
            token_file.write_text(
                json.dumps(
                    {
                        "access_token": "tok_abc",
                        "scope": "https://www.googleapis.com/auth/youtube.upload",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                creds = resolve_credentials(dotenv_path=env_file, token_file=token_file)
            self.assertTrue(creds["write_scope_granted"])
            self.assertTrue(creds["upload_scope_granted"])
            summary = redact_credential_summary(creds)
            self.assertTrue(summary["upload_scope_granted"])

    def test_safe_write_text_file_exclusive_overwrite_and_symlink_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "out.json"
            safe_write_text_file(target, '{"a": 1}\n', overwrite=False)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 1}\n')

            with self.assertRaises(YouTubeError):
                safe_write_text_file(target, '{"a": 2}\n', overwrite=False)

            safe_write_text_file(target, '{"a": 2}\n', overwrite=True)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 2}\n')

            link_path = root / "symlink.json"
            try:
                os.symlink(target, link_path)
                symlink_created = True
            except (OSError, NotImplementedError):
                symlink_created = False
            if symlink_created:
                with self.assertRaises(YouTubeError):
                    _reject_symlink_chain(link_path)

    def test_client_401_refresh_and_retry(self) -> None:
        client = YouTubeClient(
            access_token="expired_tok",
            refresh_token="ref_tok",
            client_id="cid",
            client_secret="csec",
        )
        calls: list[str] = []

        class FakeResp:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def read(self, _n: int = -1) -> bytes:
                return self._body

            def __enter__(self) -> FakeResp:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

        def fake_open(req: urllib.request.Request, timeout: float = 30.0) -> FakeResp:
            url = req.full_url
            calls.append(url)
            if "oauth2.googleapis.com/token" in url:
                return FakeResp(json.dumps({"access_token": "fresh_tok"}).encode("utf-8"))
            auth = req.get_header("Authorization") or ""
            if "expired_tok" in auth:
                raise urllib.error.HTTPError(
                    url,
                    401,
                    "Unauthorized",
                    email.message.Message(),
                    io.BytesIO(b'{"error":{"message":"Token expired"}}'),
                )
            return FakeResp(json.dumps({"items": [{"id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"}]}).encode("utf-8"))

        with patch.object(client._opener, "open", side_effect=fake_open):
            res = client.request_json("GET", "https://www.googleapis.com/youtube/v3/channels", params={"mine": "true"})
        self.assertEqual(res["items"][0]["id"], "UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.assertEqual(client.access_token, "fresh_tok")
        self.assertEqual(len(calls), 3)


class QuotaPlannerTests(unittest.TestCase):
    def test_uploads_playlist_vs_search_cost_and_zero_videos(self) -> None:
        inv0 = inventory_quota_cost(0)
        self.assertEqual(inv0["pages_of_50"], 0)
        self.assertEqual(inv0["uploads_playlist_route"]["total_units"], 1)

        inv = inventory_quota_cost(100)
        self.assertEqual(inv["pages_of_50"], 2)
        self.assertEqual(inv["uploads_playlist_route"]["total_units"], 5)

    def test_multi_day_wave_splitting_and_reserve_validation(self) -> None:
        plan = plan_quota_budget(inventory_videos=250, metadata_updates=250)
        self.assertFalse(plan["fits_in_single_day"])
        self.assertGreaterEqual(plan["estimated_days_required"], 2)
        self.assertEqual(sum(w["items"] for w in plan["recommended_waves"]), 250)
        wave1_total = plan["breakdown"]["inventory_units"] + plan["recommended_waves"][0]["estimated_units"]
        self.assertLessEqual(wave1_total, plan["usable_daily_units"])

        with self.assertRaises(ValueError):
            plan_quota_budget(daily_limit=1000, safety_reserve=1000)
        with self.assertRaises(ValueError):
            plan_quota_budget(daily_limit=0, safety_reserve=0)


class InventoryAndMetadataTests(unittest.TestCase):
    def test_iso8601_duration_urls_and_normalization(self) -> None:
        self.assertEqual(parse_iso8601_duration("PT1H2M3S"), 3723)
        self.assertEqual(parse_iso8601_duration("PT45S"), 45)
        self.assertEqual(parse_iso8601_duration("PT10M"), 600)
        self.assertEqual(parse_iso8601_duration("P1W"), 604800)
        self.assertEqual(parse_iso8601_duration("P1WT2H"), 612000)

        urls = extract_urls("See (https://en.wikipedia.org/wiki/Python_(programming_language)) and https://cto-legends.com.")
        self.assertEqual(
            urls,
            [
                "https://en.wikipedia.org/wiki/Python_(programming_language)",
                "https://cto-legends.com",
            ],
        )

        item = {
            "id": "dQw4w9WgXcQ",
            "etag": "etag_1",
            "snippet": {
                "title": "Why AI Agents Need CLI Spines",
                "description": "00:00 Intro\n01:30 Architecture\n04:00 Benchmark\nFull stack: https://cto-legends.com",
                "tags": ["ai", "cli"],
                "categoryId": "28",
                "defaultLanguage": "en",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
            "contentDetails": {"duration": "PT10M15S", "caption": "true"},
            "statistics": {"viewCount": "4200", "likeCount": "310", "commentCount": "42"},
        }
        norm = normalize_api_video_item(item)
        self.assertEqual(norm["format"], "long")
        self.assertTrue(norm["midroll_eligible"])
        self.assertEqual(norm["chapter_count"], 3)
        self.assertEqual(norm["urls"], ["https://cto-legends.com"])

    def test_legends_lowercase_title_preserves_i_and_god(self) -> None:
        self.assertEqual(legends_lowercase_title("God Loves Us And God's Grace"), "God loves us and God's grace")
        self.assertEqual(legends_lowercase_title("Why I Built God's Tool"), "why I built God's tool")
        self.assertEqual(legends_lowercase_title("Why CTO Legends Ships Fast"), "why cto legends ships fast")

    def test_lossless_snippet_merge_etag_and_guardrails(self) -> None:
        initial = {
            "dQw4w9WgXcQ": {
                "id": "dQw4w9WgXcQ",
                "etag": "etag_init",
                "snippet": {
                    "channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                    "title": "Old Title",
                    "description": "Keep this description intact\nLine two",
                    " categoryId": "28",
                    "categoryId": "28",
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en-US",
                },
                "status": {"privacyStatus": "public"},
            }
        }
        fake_client = FakeYouTubeClient(initial)
        plan = validate_metadata_plan(
            {
                "schemaVersion": 1,
                "channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "allowedVideoIds": ["dQw4w9WgXcQ"],
                "updates": [
                    {
                        "videoId": "dQw4w9WgXcQ",
                        "expectedCurrent": {
                            "title": "Old Title",
                            "description": "Keep this description intact\r\nLine two",
                        },
                        "title": "New Title",
                    }
                ],
            }
        )
        sha = canonical_plan_sha256(plan)
        with self.assertRaises(YouTubeError):
            execute_metadata_plan(fake_client, plan, expected_plan_sha256="", confirm=True)

        receipt = execute_metadata_plan(fake_client, plan, expected_plan_sha256=sha, confirm=True)
        self.assertEqual(receipt["youtube_mutations"], 1)
        self.assertEqual(receipt["forbidden_surface_mutations"], 0)
        sent_snippet = fake_client.update_calls[0]["snippet"]
        self.assertEqual(sent_snippet["title"], "New Title")
        self.assertEqual(sent_snippet["description"], "Keep this description intact\nLine two")
        self.assertEqual(sent_snippet["categoryId"], "28")
        self.assertEqual(sent_snippet["defaultLanguage"], "en")

        # Drift failure when expectedCurrent no longer matches live title
        with self.assertRaises(YouTubeError):
            execute_metadata_plan(fake_client, plan, expected_plan_sha256=sha, confirm=True)

        # Channel ID mismatch failure
        wrong_channel_plan = validate_metadata_plan(
            {
                "schemaVersion": 1,
                "channelId": "UC1111111111111111111111",
                "allowedVideoIds": ["dQw4w9WgXcQ"],
                "updates": [{"videoId": "dQw4w9WgXcQ", "title": "Another Title"}],
            }
        )
        with self.assertRaises(YouTubeError):
            execute_metadata_plan(
                fake_client,
                wrong_channel_plan,
                expected_plan_sha256=canonical_plan_sha256(wrong_channel_plan),
                confirm=True,
            )

        # Reject angle brackets and missing categoryId
        with self.assertRaises(YouTubeError):
            validate_metadata_plan(
                {
                    "schemaVersion": 1,
                    "allowedVideoIds": ["dQw4w9WgXcQ"],
                    "updates": [{"videoId": "dQw4w9WgXcQ", "title": "Bad <angle> title"}],
                }
            )
        with self.assertRaises(YouTubeError):
            build_merged_snippet({"title": "T", "description": "D"}, {"videoId": "dQw4w9WgXcQ", "title": "New"})
        with self.assertRaises(YouTubeError):
            generate_link_migration_plan([], find_url="", replace_url="", set_exact_description=None)


class AnalyticsAndStudioLintTests(unittest.TestCase):
    def test_analytics_scorecard_ctr_percent_and_packaging_audit(self) -> None:
        raw = [
            {
                "video_id": "vid_high_ctr",
                "title": "High CTR Video",
                "format": "long",
                "length_seconds": 900,
                "impressions": 20000,
                "impressions_ctr": 8.0,  # 8.0% passed as percentage (1 < ctr <= 100)
                "views": 1600,
                "average_view_duration_seconds": 500,
                "subscribers_gained": 40,
                "estimated_revenue_usd": 32.0,
            },
            {
                "video_id": "vid_low_ctr",
                "title": "Low CTR Video",
                "format": "long",
                "length_seconds": 400,
                "impressions": 50000,
                "impressions_ctr": 0.025,
                "views": 1250,
                "average_view_duration_seconds": 220,
                "subscribers_gained": 10,
                "estimated_revenue_usd": 15.0,
            },
        ]
        records = normalize_records(raw)
        by_id = {r["video_id"]: r for r in records}
        self.assertAlmostEqual(by_id["vid_high_ctr"]["impressions_ctr"], 0.08)
        health = channel_health(records)
        self.assertEqual(health["video_count"], 2)
        self.assertTrue(any("under 8 minutes" in f for f in health["flags"]))
        pkg = packaging_audit(records, min_impressions=1000)
        self.assertEqual(pkg["candidate_count"], 1)
        self.assertEqual(pkg["candidates"][0]["video_id"], "vid_low_ctr")
        md = render_scorecard_markdown(records, channel_name="Test Channel")
        self.assertIn("Test Channel", md)

    def test_chapters_and_quiz_lint_rejects_bool_correct_index(self) -> None:
        good_desc = "00:00 Hook and Problem\n02:15 The Partial Update Trap\n06:30 Quota Math\n12:00 Live Demo"
        chap_res = lint_chapters(good_desc, video_duration_seconds=900)
        self.assertTrue(chap_res["valid"])
        self.assertEqual(chap_res["chapter_count"], 4)

        bad_desc = "00:30 Missing Zero Start\n01:00 Too Few Chapters"
        bad_chap = lint_chapters(bad_desc, video_duration_seconds=300)
        self.assertFalse(bad_chap["valid"])

        quiz_payload = {
            "quizzes": [
                {
                    "timestamp": "05:25:00",
                    "question": "When calling YouTube Data API v3 videos.update(part='snippet'), what happens to omitted mutable snippet properties?",
                    "correct_index": 1,
                    "options": [
                        "YouTube preserves existing tags, description, and language on the server",
                        "YouTube deletes any omitted mutable snippet fields unless merged first",
                        "YouTube returns HTTP 400 unless every optional tag field is explicitly set",
                        "YouTube creates a new revision draft without mutating the public video",
                    ],
                    "explanation": "Omitted mutable properties inside snippet are deleted unless merged from preflight.",
                }
            ]
        }
        quiz_res = lint_studio_quizzes(quiz_payload, video_duration_seconds=1800)
        self.assertTrue(quiz_res["valid"])
        self.assertEqual(quiz_res["quiz_count"], 1)

        bool_quiz = json.loads(json.dumps(quiz_payload))
        bool_quiz["quizzes"][0]["correct_index"] = True
        bool_res = lint_studio_quizzes(bool_quiz, video_duration_seconds=1800)
        self.assertFalse(bool_res["valid"])


class UploadAndCliTests(unittest.TestCase):
    def test_thumbnail_draft_freeze_tamper_and_resumable_upload_apply(self) -> None:
        self.assertEqual(_video_mime_type(Path("clip.mov")), "video/quicktime")
        self.assertEqual(_video_mime_type(Path("clip.mp4")), "video/mp4")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vid = root / "video.mov"
            title = root / "title.txt"
            desc = root / "description.txt"
            thumb = root / "thumb.png"

            vid.write_bytes(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 2048)
            title.write_text("why legends-youtube protects channel metadata\n", encoding="utf-8")
            desc.write_text("00:00 Intro\n01:00 Deep Dive\n03:00 Conclusion\nhttps://cto-legends.com\n", encoding="utf-8")
            thumb.write_bytes(_make_minimal_png(1280, 720))

            thumb_info = inspect_thumbnail(thumb)
            self.assertTrue(thumb_info["valid"])
            self.assertEqual(thumb_info["width"], 1280)
            self.assertEqual(thumb_info["height"], 720)

            frozen = freeze_draft_plan(
                video_path=vid,
                title_path=title,
                description_path=desc,
                thumbnail_path=thumb,
                channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
                notify_subscribers=False,
            )
            verified = verify_frozen_draft_plan(frozen)
            self.assertEqual(verified["privacyStatus"], "private")
            self.assertFalse(verified["notifySubscribers"])

            # Tamper detection on plan_sha256 and title
            tampered_hash = json.loads(json.dumps(frozen))
            tampered_hash["plan_sha256"] = "0" * 64
            with self.assertRaises(YouTubeError):
                verify_frozen_draft_plan(tampered_hash)

            tampered_title = json.loads(json.dumps(frozen))
            tampered_title["plan"]["title"] = "injected title"
            with self.assertRaises(YouTubeError):
                verify_frozen_draft_plan(tampered_title)
            # Even if plan_sha256 is absent/bypassed on inner plan dict, disk title mismatch is caught
            with self.assertRaises(YouTubeError):
                verify_frozen_draft_plan(tampered_title["plan"])

            dry_upload = execute_private_draft_upload(YouTubeClient(), frozen, apply=False)
            self.assertEqual(dry_upload["mode"], "dry_run_verified")

            # Live apply=True with mocked resumable session (308 Range -> 200 final) and channel mismatch check
            mismatch_client = YouTubeClient(access_token="tok")
            with patch.object(mismatch_client, "get_channel", return_value={"id": "UC1111111111111111111111"}):
                with self.assertRaises(YouTubeError):
                    execute_private_draft_upload(
                        mismatch_client,
                        frozen,
                        confirm_phrase="UPLOAD_PRIVATE_DRAFT UC_x5XG1OV2P6uZZ5FSM9Ttw",
                        apply=True,
                    )

            live_client = YouTubeClient(access_token="tok")
            seen_requests: list[urllib.request.Request] = []
            put_attempt = 0

            class FakeHttpResp:
                def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
                    self.status = status
                    self.headers = headers
                    self._body = body

                def read(self, _n: int = -1) -> bytes:
                    return self._body

                def __enter__(self) -> FakeHttpResp:
                    return self

                def __exit__(self, *args: Any) -> None:
                    pass

            def fake_opener_open(req: urllib.request.Request, timeout: float = 60.0) -> FakeHttpResp:
                nonlocal put_attempt
                seen_requests.append(req)
                if req.get_method() == "POST" and "uploadType=resumable" in req.full_url:
                    return FakeHttpResp(
                        200,
                        {"Location": "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=session123"},
                        b"",
                    )
                if req.get_method() == "PUT":
                    put_attempt += 1
                    if put_attempt == 1:
                        # Simulate partial 308 Resume Incomplete after first 1024 bytes
                        hdrs = email.message.Message()
                        hdrs["Range"] = "bytes=0-1023"
                        raise urllib.error.HTTPError(
                            req.full_url,
                            308,
                            "Resume Incomplete",
                            hdrs,
                            io.BytesIO(b""),
                        )
                    return FakeHttpResp(
                        200,
                        {},
                        json.dumps({"id": "VidLong0001", "status": {"privacyStatus": "private"}}).encode("utf-8"),
                    )
                if "thumbnails/set" in req.full_url:
                    return FakeHttpResp(200, {}, b'{"items":[{"default":{"url":"https://i.ytimg.com/vi/VidLong0001/default.jpg"}}]}')
                raise AssertionError(f"Unexpected request: {req.full_url}")

            with (
                patch.object(live_client, "get_channel", return_value={"id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"}),
                patch.object(live_client._opener, "open", side_effect=fake_opener_open),
            ):
                upload_res = execute_private_draft_upload(
                    live_client,
                    frozen,
                    confirm_phrase="UPLOAD_PRIVATE_DRAFT UC_x5XG1OV2P6uZZ5FSM9Ttw",
                    apply=True,
                )

            self.assertEqual(upload_res["mode"], "uploaded_private_draft")
            self.assertEqual(upload_res["video_id"], "VidLong0001")
            self.assertEqual(upload_res["privacy_status"], "private")
            self.assertEqual(upload_res["channel_id"], "UC_x5XG1OV2P6uZZ5FSM9Ttw")
            init_req = seen_requests[0]
            self.assertEqual(init_req.get_header("X-upload-content-type"), "video/quicktime")
            self.assertEqual(put_attempt, 2)

    def test_cli_doctor_knowledge_pack_and_lint_exit_codes(self) -> None:
        res = resolve_resources()
        self.assertTrue(res["complete"], res.get("note"))
        self.assertEqual(res["verified_files"], 18)

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli_main(["doctor", "--json"])
        self.assertEqual(code, 0)
        out = json.loads(buf.getvalue())
        self.assertTrue(out["ok"])
        self.assertEqual(out["module"], "legends-youtube")

        with tempfile.TemporaryDirectory() as tmp:
            desc_file = Path(tmp) / "desc.txt"
            desc_file.write_text("Clean description with https://cto-legends.com\n", encoding="utf-8")

            buf_ok = io.StringIO()
            with redirect_stdout(buf_ok):
                rc_ok = cli_main(
                    [
                        "house-style-lint",
                        "--title",
                        "why I built God's tool",
                        "--description-file",
                        str(desc_file),
                        "--cta-block",
                        "https://cto-legends.com",
                    ]
                )
            self.assertEqual(rc_ok, 0)
            self.assertTrue(json.loads(buf_ok.getvalue())["valid"])

            buf_fail = io.StringIO()
            with redirect_stdout(buf_fail):
                rc_fail = cli_main(["house-style-lint", "--title", "Bad Uppercase #shorts"])
            self.assertEqual(rc_fail, 1)
            self.assertFalse(json.loads(buf_fail.getvalue())["valid"])

            buf_rel = io.StringIO()
            with redirect_stdout(buf_rel):
                rc_rel = cli_main(["related-guard", "--video-ids", "VidLong0001", "--target", "VidLong0001"])
            self.assertEqual(rc_rel, 1)
            self.assertFalse(json.loads(buf_rel.getvalue())["valid"])

            # Test --no-json plain output and --output on paths
            paths_out = Path(tmp) / "paths.json"
            buf_plain = io.StringIO()
            with redirect_stdout(buf_plain):
                rc_paths = cli_main(["paths", "--no-json", "--output", str(paths_out)])
            self.assertEqual(rc_paths, 0)
            self.assertTrue(paths_out.is_file())
            self.assertIn("source:", buf_plain.getvalue())

    def test_perfect_video_score_related_guard_and_house_style(self) -> None:
        idea = score_video_idea(
            title="I Built a Codex System to Find My Next YouTube Video",
            days_since_catalyst=14,
            trend_timing=8,
            search_surface=8,
            audience_pain=9,
            channel_dna_fit=10,
            proof_advantage=9,
            packaging_strength=8,
            production_drag=3,
            platform_risk=1,
            hype_saturation=2,
            fit_checks_passed=8,
        )
        self.assertTrue(idea["greenlight"])
        self.assertEqual(idea["timing"]["stage"], "goldilocks_prime_day_4_30")

        guard_ok = validate_related_video_guard(
            ["VidShrt0001", "VidShrt0002"],
            "VidLong0001",
            confirm=True,
            phrase="LINK_RELATED_BATCH 2 -> VidLong0001",
        )
        self.assertTrue(guard_ok["valid"])
        self.assertEqual(guard_ok["mode"], "live_confirmed")

        guard_self = validate_related_video_guard(["VidLong0001"], "VidLong0001")
        self.assertFalse(guard_self["valid"])

        style_ok = lint_house_style("I made God's grace visible in ai", "clean body\nhttps://cto-legends.com")
        self.assertTrue(style_ok["valid"])
        style_bad = lint_house_style("Why Uppercase Fails #shorts", "spam #seo")
        self.assertFalse(style_bad["valid"])

        html = 'prefix var ytInitialPlayerResponse = {"playabilityStatus":{"status":"OK"},"videoDetails":{"videoId":"dQw4w9WgXcQ"}}; suffix'
        extracted = _extract_balanced_json(html, "var ytInitialPlayerResponse = ")
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted["videoDetails"]["videoId"], "dQw4w9WgXcQ")

    def test_engagement_comments_playlists_and_funnel(self) -> None:
        comments = [
            {"id": "c1", "author": "Alice", "text": "Can you do a tutorial on how to wire quota waves?", "likes": 12},
            {"id": "c2", "author": "Bob", "text": "The diagram at 04:15 made everything click!", "likes": 3},
            {"id": "c3", "author": "Bot", "text": "Message me on WhatsApp or https://scam.example for crypto!", "likes": 0},
        ]
        triaged = triage_comments(comments)
        self.assertEqual(triaged["question_count"], 1)
        self.assertEqual(triaged["timestamp_citation_count"], 1)
        self.assertEqual(triaged["spam_candidate_count"], 1)

        videos = [
            {"video_id": "VidLong0001", "title": "Long 1", "format": "long", "privacy_status": "public", "views": 5000, "description": "https://cto-legends.com"},
            {"video_id": "VidLong0002", "title": "Long 2 Orphan", "format": "long", "privacy_status": "public", "views": 1200, "description": "https://cto-legends.com"},
            {"video_id": "VidShrt0001", "title": "Short 1", "format": "short", "privacy_status": "public", "views": 8000, "description": "Watch VidLong0001"},
        ]
        playlists = [
            {"playlist_id": "PL1234567890abcdef", "title": "Main Series", "video_ids": ["VidLong0001", "VidLong0001"]}
        ]
        pl_audit = audit_playlists(videos, playlists)
        self.assertEqual(pl_audit["orphaned_public_long_count"], 1)
        self.assertEqual(pl_audit["playlists"][0]["duplicate_video_ids"], ["VidLong0001"])

        funnel = audit_shorts_funnel(videos, canonical_cta="https://cto-legends.com")
        self.assertEqual(funnel["public_shorts_count"], 1)
        self.assertEqual(funnel["shorts_with_long_description_link_count"], 1)
        self.assertEqual(funnel["shorts_missing_cta_count"], 1)

    def test_intelligence_transcript_formats_xml_safety_outliers_and_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            t_path = root / "sample.json"
            t_path.write_text(
                json.dumps(
                    {
                        "duration": 180.0,
                        "segments": [
                            {"start": 0.0, "end": 12.0, "text": "I wanted to talk about building an agentic YouTube control plane that never wipes tags."},
                            {"start": 12.0, "end": 38.0, "text": "Most people lose their metadata when calling partial updates without merging live fields first."},
                            {"start": 40.5, "end": 75.0, "text": "How to build a zero quota public readback probe using the watch page and oembed."},
                            {"start": 76.5, "end": 125.0, "text": "The second one is the Shorts related video funnel that routes viewers to long form."},
                            {"start": 127.0, "end": 180.0, "text": "What is currently working across top technical channels on YouTube right now."},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            pkg = compile_transcript_package(t_path, video_title="Agentic YouTube Control", min_chapter_seconds=30)
            self.assertTrue(pkg["chapters"]["valid"])
            self.assertGreaterEqual(pkg["chapters"]["chapter_count"], 3)
            self.assertGreaterEqual(pkg["pacing_audit"]["dead_air_gap_count"], 2)

            # Test .srt, .vtt (with MM:SS.mmm and NOTE), and bracketed .txt transcript parsing
            srt_path = root / "captions.srt"
            srt_path.write_text(
                "1\n00:00:00,000 --> 00:00:10,500\nFirst spoken line in SRT.\n\n"
                "2\n00:00:12,000 --> 00:00:25,000\nSecond spoken line in SRT.\n",
                encoding="utf-8",
            )
            srt_res = load_transcript_segments(srt_path)
            self.assertEqual(len(srt_res["segments"]), 2)
            self.assertAlmostEqual(srt_res["segments"][0]["end"], 10.5)

            vtt_path = root / "captions.vtt"
            vtt_path.write_text(
                "WEBVTT\nKind: captions\nLanguage: en\n\nNOTE comment line\n\n"
                "00:00.000 --> 00:08.250\nShort form VTT cue without hours.\n\n"
                "00:01:00.000 --> 00:01:15.000\nFull hour VTT cue.\n",
                encoding="utf-8",
            )
            vtt_res = load_transcript_segments(vtt_path)
            self.assertEqual(len(vtt_res["segments"]), 2)
            self.assertAlmostEqual(vtt_res["segments"][0]["end"], 8.25)
            self.assertAlmostEqual(vtt_res["segments"][1]["start"], 60.0)

            txt_path = root / "notes.txt"
            txt_path.write_text("[  0.00 -  12.50] Opening hook line\n[ 12.50 -  75.00] Deep dive section\n", encoding="utf-8")
            txt_res = load_transcript_segments(txt_path)
            self.assertEqual(len(txt_res["segments"]), 2)
            self.assertEqual(txt_res["segments"][1]["start"], 12.5)

            xray = correlate_retention_with_transcript(
                t_path,
                {"rows": [[0.0, 1.0], [0.2, 0.72], [0.5, 0.76], [1.0, 0.48]]},
            )
            self.assertGreaterEqual(xray["dropoff_cliff_count"], 1)
            self.assertEqual(xray["rewatch_spike_count"], 1)

        # XML parser rejects <!DOCTYPE and <!ENTITY (even after >4 KB padding) and malformed XML
        with self.assertRaises(YouTubeError):
            _safe_parse_xml_bytes(b'<?xml version="1.0"?><!DOCTYPE feed [<!ENTITY xxe "boom">]><feed>&xxe;</feed>')
        with self.assertRaises(YouTubeError):
            _safe_parse_xml_bytes(b" " * 5000 + b"<!DOCTYPE feed><feed/>")
        with self.assertRaises(YouTubeError):
            _safe_parse_xml_bytes(b"<feed><unclosed></feed>")

        outliers = scout_channel_outliers(
            [
                {"video_id": "VidLong0001", "title": "baseline video 1", "views": 100, "published_at": "2026-10-01T00:00:00Z"},
                {"video_id": "VidLong0002", "title": "baseline video 2", "views": 110, "published_at": "2026-10-01T00:00:00Z"},
                {"video_id": "VidOutlr001", "title": "open source + up to 80x cheaper", "views": 950, "published_at": "2026-10-20T00:00:00Z"},
            ],
            outlier_threshold_multiplier=2.0,
        )
        self.assertEqual(outliers["outlier_count"], 1)
        self.assertEqual(outliers["outliers"][0]["video_id"], "VidOutlr001")

    def test_carbon_pass2_malformed_json_nan_vtt_date_and_api_url_guards(self) -> None:
        # 1. Malformed JSON shapes
        with self.assertRaises(ValueError):
            normalize_records("not-a-list")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            triage_comments(123)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            triage_comments(["not-a-dict"])  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            normalize_comment_thread_item({"id": "c1", "likes": "bad-int"})
        # Malformed topLevelComment string instead of dict falls back cleanly without AttributeError
        norm_c = normalize_comment_thread_item(
            {"id": "c2", "snippet": {"topLevelComment": "oops", "textOriginal": "Hello world"}}
        )
        self.assertEqual(norm_c["text"], "Hello world")

        with self.assertRaises(ValueError):
            audit_playlists([], "not-a-list")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            audit_playlists([], ["not-a-dict"])  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            audit_playlists([], [{"playlist_id": "PL1234567890", "video_ids": 999}])
        with self.assertRaises(ValueError):
            audit_shorts_funnel("not-a-list")  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            lint_studio_quizzes({"quizzes": "not-a-list"})
        with self.assertRaises(ValueError):
            lint_studio_quizzes({"quizzes": [], "video_duration_seconds": True})
        with self.assertRaises(ValueError):
            lint_studio_quizzes({"quizzes": [], "video_duration_seconds": "bad"})

        links_res = audit_description_links(
            [{"video_id": "dQw4w9WgXcQ", "title": "t", "urls": [123, None, "https://cto-legends.com"]}]
        )
        self.assertEqual(links_res["unique_url_count"], 1)

        with self.assertRaises(YouTubeError):
            verify_frozen_draft_plan(
                {
                    "privacyStatus": "private",
                    "channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                    "paths": ["not-a-dict"],
                    "sha256": {},
                }
            )

        # 2. NaN / Infinity / None float guards
        with self.assertRaises(ValueError):
            score_video_idea(title="bad", trend_timing=float("nan"))
        with self.assertRaises(ValueError):
            packaging_audit([], min_impressions=float("inf"))
        with self.assertRaises(YouTubeError):
            scout_channel_outliers(
                [{"video_id": "dQw4w9WgXcQ", "title": "t", "views": float("nan")}]
            )

        # 3. WebVTT multi-line NOTE/STYLE and alphanumeric cue IDs after first cue
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vtt_complex = root / "complex.vtt"
            vtt_complex.write_text(
                "WEBVTT\n\n"
                "NOTE first line of note\n"
                "second line of note that must not leak\n\n"
                "STYLE\n"
                "::cue { color: lime; }\n\n"
                "cue-alpha\n"
                "00:00.000 --> 00:05.000\n"
                "First spoken cue text.\n\n"
                "NOTE mid-file multi-line note\n"
                "should also be ignored completely\n\n"
                "cue-beta\n"
                "00:06.000 --> 00:12.000\n"
                "Second spoken cue text.\n",
                encoding="utf-8",
            )
            parsed_vtt = load_transcript_segments(vtt_complex)
            self.assertEqual(len(parsed_vtt["segments"]), 2)
            self.assertEqual(parsed_vtt["segments"][0]["text"], "First spoken cue text.")
            self.assertEqual(parsed_vtt["segments"][1]["text"], "Second spoken cue text.")

            # Retention X-ray with explicit None in dict fields and NaN rejection
            t_json = root / "t.json"
            t_json.write_text(
                json.dumps({"duration": 60.0, "segments": [{"start": 0.0, "end": 30.0, "text": "Hook"}, {"start": 30.0, "end": 60.0, "text": "End"}]}),
                encoding="utf-8",
            )
            xray_none = correlate_retention_with_transcript(
                t_json,
                [{"elapsed_ratio": 0.0, "watch_ratio": 1.0, "relative": None}, {"elapsed_ratio": 0.5, "watch_ratio": 0.7, "relative": None}],
            )
            self.assertEqual(xray_none["points_analyzed"], 2)
            with self.assertRaises(YouTubeError):
                correlate_retention_with_transcript(
                    t_json,
                    [{"elapsed_ratio": float("nan"), "watch_ratio": 1.0}, {"elapsed_ratio": 0.5, "watch_ratio": 0.7}],
                )

            # 4. CLI analytics-audit --live inverted date range and CLI NaN float rejection
            err_buf = io.StringIO()
            with redirect_stderr(err_buf):
                rc_dates = cli_main(
                    ["analytics-audit", "--live", "--start-date", "2026-12-01", "--end-date", "2026-01-01"]
                )
            self.assertEqual(rc_dates, 1)
            self.assertIn("start-date", json.loads(err_buf.getvalue())["error"])

            with self.assertRaises(SystemExit):
                with redirect_stderr(io.StringIO()):
                    cli_main(["score-idea", "--title", "test", "--trend-timing", "nan"])

        # 5. API URL validation (credentials & port) and mid-stream HTTPException handling
        client = YouTubeClient(api_key="test-key")
        with self.assertRaises(YouTubeError):
            client._validate_api_url("https://user:pass@www.googleapis.com/youtube/v3/videos")
        with self.assertRaises(YouTubeError):
            client._validate_api_url("https://www.googleapis.com:8443/youtube/v3/videos")
        with patch.object(client._opener, "open", side_effect=http.client.IncompleteRead(b"part", 100)):
            with self.assertRaises(YouTubeError):
                client.request_json("GET", f"{client.data_base_url}/videos")

    def test_ytdlp_subcommand_delegation(self) -> None:
        """Verify legends-youtube delegates yt-dlp, archive, pull, transcribe, and clips cleanly to legends_ytdlp."""
        with patch("legends_ytdlp.cli.main", return_value=0) as mock_ytdlp_main:
            self.assertEqual(cli_main(["yt-dlp"]), 0)
            mock_ytdlp_main.assert_called_with(["--help"])

            self.assertEqual(cli_main(["yt-dlp", "--help"]), 0)
            mock_ytdlp_main.assert_called_with(["--help"])

            self.assertEqual(cli_main(["yt-dlp", "doctor", "--offline"]), 0)
            mock_ytdlp_main.assert_called_with(["doctor", "--offline"])

            self.assertEqual(cli_main(["yt-dlp", "check"]), 0)
            mock_ytdlp_main.assert_called_with(["yt-dlp", "check"])

            self.assertEqual(cli_main(["archive", "https://www.youtube.com/@test"]), 0)
            mock_ytdlp_main.assert_called_with(["inventory", "https://www.youtube.com/@test"])

            self.assertEqual(cli_main(["pull", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]), 0)
            mock_ytdlp_main.assert_called_with(["plan", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

            self.assertEqual(cli_main(["transcribe", "batches/b1/manifest.json", "--all"]), 0)
            mock_ytdlp_main.assert_called_with(["intelligence", "transcribe", "batches/b1/manifest.json", "--all"])

            self.assertEqual(cli_main(["clips", "plan", "batches/b1/manifest.json", "--query", "agent"]), 0)
            mock_ytdlp_main.assert_called_with(["intelligence", "clips", "plan", "batches/b1/manifest.json", "--query", "agent"])


if __name__ == "__main__":
    unittest.main()
