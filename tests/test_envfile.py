import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legends_ytdlp.envfile import read_env_file, redact, resolve_mullvad_account
from legends_ytdlp.paths import resolve_local_dir, resolve_workspace_root


class EnvFileTests(unittest.TestCase):
    def test_read_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("A=1\n# ignored\nB=\"two\"\n\n", encoding="utf-8")
            self.assertEqual(read_env_file(env), {"A": "1", "B": "two"})

    def test_read_env_file_refuses_symlink_and_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_bytes(b"A=" + b"1" * (70 * 1024))
            with self.assertRaisesRegex(ValueError, "exceeds maximum"):
                read_env_file(env)
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    read_env_file(env)

    def test_resolve_mullvad_account_and_wheel_safe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "custom.env"
            env_file.write_text("MULLVAD_ACCOUNT_NUMBER=1234567890123456\n", encoding="utf-8")
            with patch.dict(os.environ, {"LEGENDS_YTDLP_ENV_FILE": str(env_file)}, clear=False):
                os.environ.pop("MULLVAD_ACCOUNT_NUMBER", None)
                self.assertEqual(resolve_mullvad_account(), "1234567890123456")
            with patch.dict(os.environ, {"MULLVAD_ACCOUNT_NUMBER": "6543210987654321"}, clear=False):
                self.assertEqual(resolve_mullvad_account(), "6543210987654321")

            with patch("legends_ytdlp.paths.IS_REPO_CHECKOUT", False), patch.dict(
                os.environ,
                {"LEGENDS_YTDLP_WORKSPACE": str(tmp), "LEGENDS_YTDLP_HOME": str(Path(tmp) / "home")},
                clear=False,
            ):
                self.assertEqual(resolve_workspace_root(), Path(tmp).resolve())
                self.assertEqual(resolve_local_dir(), (Path(tmp) / "home").resolve())

    def test_redact_keeps_tail(self) -> None:
        self.assertEqual(redact("1234567890"), "******7890")
        self.assertEqual(redact(None), "<missing>")

