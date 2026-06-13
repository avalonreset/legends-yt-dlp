import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from slayer_cli.cli import LEGAL_USE_NOTICE, cmd_run
from slayer_cli.doctor import Check
from slayer_cli.mullvad import ShutdownResult
from slayer_cli.process import CommandResult


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
                no_production=False,
                no_require_connected=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=False,
            )
            stdout = io.StringIO()
            with (
                patch("slayer_cli.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("slayer_cli.cli.preflight_ok", return_value=True),
                patch("slayer_cli.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("slayer_cli.cli.write_run_report", return_value=report),
                patch("slayer_cli.cli.shutdown_connection", return_value=ShutdownResult(True, ("Mullvad shutdown verified.",))) as shutdown,
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
                no_production=False,
                no_require_connected=False,
                recover_vpn=True,
                vpn_recovery_attempts=0,
                vpn_recovery_wait=0.0,
                yes=True,
                show_output=False,
                keep_vpn=True,
            )
            with (
                patch("slayer_cli.cli.preflight_batch", return_value=[Check("manifest", True, str(manifest))]),
                patch("slayer_cli.cli.preflight_ok", return_value=True),
                patch("slayer_cli.cli.run_batch", return_value=CommandResult(("yt-dlp",), 0, "", "")),
                patch("slayer_cli.cli.write_run_report", return_value=report),
                patch("slayer_cli.cli.shutdown_connection") as shutdown,
            ):
                self.assertEqual(cmd_run(args), 0)

            shutdown.assert_not_called()
