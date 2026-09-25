import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legends_ytdlp.cli import LEGAL_USE_NOTICE, cmd_run, cmd_ytdlp_check
from legends_ytdlp.doctor import Check
from legends_ytdlp.mullvad import ShutdownResult
from legends_ytdlp.process import CommandResult


class CliTests(unittest.TestCase):
    def test_real_run_prints_legal_use_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            report = root / "report.json"
            report.write_text(json.dumps({"status": "completed", "classification": "ok", "ledger": {}}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=True,
                bulk=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            stdout = io.StringIO()
            with (
                patch("legends_ytdlp.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("legends_ytdlp.cli.preflight_ok", return_value=True),
                patch("legends_ytdlp.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("legends_ytdlp.cli.write_run_report", return_value=report),
                patch("legends_ytdlp.cli.shutdown_connection", return_value=ShutdownResult(True, ("Mullvad shutdown verified.",))) as shutdown,
                contextlib.redirect_stdout(stdout),
            ):
                self.assertEqual(cmd_run(args), 0)

            self.assertIn(LEGAL_USE_NOTICE, stdout.getvalue())
            self.assertIn("Mullvad shutdown verified.", stdout.getvalue())
            shutdown.assert_called_once_with()

    def test_keep_vpn_skips_post_run_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            report = root / "report.json"
            report.write_text(json.dumps({"status": "completed", "classification": "ok", "ledger": {}}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=True,
                bulk=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=True,
            )
            with (
                patch("legends_ytdlp.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("legends_ytdlp.cli.preflight_ok", return_value=True),
                patch("legends_ytdlp.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("legends_ytdlp.cli.write_run_report", return_value=report),
                patch("legends_ytdlp.cli.shutdown_connection") as shutdown,
            ):
                self.assertEqual(cmd_run(args), 0)

            shutdown.assert_not_called()

    def test_default_run_skips_vpn_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            report = root / "report.json"
            report.write_text(json.dumps({"status": "completed", "classification": "ok", "ledger": {}}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=False,
                bulk=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            with (
                patch("legends_ytdlp.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("legends_ytdlp.cli.preflight_ok", return_value=True),
                patch("legends_ytdlp.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("legends_ytdlp.cli.write_run_report", return_value=report),
                patch("legends_ytdlp.cli.shutdown_connection") as shutdown,
            ):
                self.assertEqual(cmd_run(args), 0)

            shutdown.assert_not_called()

    def test_bulk_batch_requires_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            urls = [f"https://example.com/video{i}" for i in range(51)]
            manifest.write_text(json.dumps({"source_urls": urls}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=False,
                bulk=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            stderr = io.StringIO()
            with (
                patch("legends_ytdlp.cli.preflight_batch") as preflight,
                contextlib.redirect_stderr(stderr),
            ):
                self.assertEqual(cmd_run(args), 2)

            self.assertIn("--bulk", stderr.getvalue())
            preflight.assert_not_called()

    def test_bulk_batch_runs_when_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            urls = [f"https://example.com/video{i}" for i in range(51)]
            manifest.write_text(json.dumps({"source_urls": urls}), encoding="utf-8")
            report = root / "report.json"
            report.write_text(json.dumps({"status": "completed", "classification": "ok", "ledger": {}}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=False,
                bulk=True,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            stdout = io.StringIO()
            with (
                patch("legends_ytdlp.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("legends_ytdlp.cli.preflight_ok", return_value=True),
                patch("legends_ytdlp.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("legends_ytdlp.cli.write_run_report", return_value=report),
                contextlib.redirect_stdout(stdout),
            ):
                self.assertEqual(cmd_run(args), 0)

            self.assertIn("acknowledged with --bulk", stdout.getvalue())

    def test_medium_batch_prints_pacing_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            urls = [f"https://example.com/video{i}" for i in range(25)]
            manifest.write_text(json.dumps({"source_urls": urls}), encoding="utf-8")
            report = root / "report.json"
            report.write_text(json.dumps({"status": "completed", "classification": "ok", "ledger": {}}), encoding="utf-8")
            args = argparse.Namespace(
                manifest=str(manifest),
                dry_run=False,
                with_vpn=False,
                bulk=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            stdout = io.StringIO()
            with (
                patch("legends_ytdlp.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("legends_ytdlp.cli.preflight_ok", return_value=True),
                patch("legends_ytdlp.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("legends_ytdlp.cli.write_run_report", return_value=report),
                contextlib.redirect_stdout(stdout),
            ):
                self.assertEqual(cmd_run(args), 0)

            self.assertIn("Medium batch (25 URLs)", stdout.getvalue())

class YtdlpCheckTests(unittest.TestCase):
    def run_check(self, info, upstream="2026.08.19"):
        args = argparse.Namespace()
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch("legends_ytdlp.cli.find_ytdlp", return_value=info),
            patch("legends_ytdlp.cli.fetch_upstream_ytdlp_version", return_value=upstream),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = cmd_ytdlp_check(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_check_current(self) -> None:
        from legends_ytdlp.tools import ToolInfo
        info = ToolInfo("yt-dlp", Path("yt-dlp.exe"), "2026.08.19", True, "ok")
        code, out, _ = self.run_check(info)
        self.assertEqual(code, 0)
        self.assertIn("yt-dlp is current.", out)

    def test_check_behind(self) -> None:
        from legends_ytdlp.tools import ToolInfo
        info = ToolInfo("yt-dlp", Path("yt-dlp.exe"), "2026.03.17", True, "ok")
        code, out, _ = self.run_check(info)
        self.assertEqual(code, 1)
        self.assertIn("Update available", out)

    def test_check_missing_binary(self) -> None:
        from legends_ytdlp.tools import ToolInfo
        info = ToolInfo("yt-dlp", None, None, False, "missing")
        code, _, err = self.run_check(info)
        self.assertEqual(code, 2)
        self.assertIn("yt-dlp install", err)

    def test_check_upstream_unreachable(self) -> None:
        from legends_ytdlp.tools import ToolInfo
        info = ToolInfo("yt-dlp", Path("yt-dlp.exe"), "2026.08.19", True, "ok")
        args = argparse.Namespace()
        stderr = io.StringIO()
        with (
            patch("legends_ytdlp.cli.find_ytdlp", return_value=info),
            patch("legends_ytdlp.cli.fetch_upstream_ytdlp_version", side_effect=RuntimeError("Could not reach the upstream yt-dlp release feed: down")),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(cmd_ytdlp_check(args), 2)
        self.assertIn("Could not reach", stderr.getvalue())
