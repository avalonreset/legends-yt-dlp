import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legends_ytdlp.batch import create_batch_from_urls, preflight_batch, preflight_ok
from legends_ytdlp.cli import cmd_doctor, cmd_run
from legends_ytdlp.doctor import Check, overall_ok, run_doctor
from legends_ytdlp.mullvad import MullvadStatus, MullvadSetting
from legends_ytdlp.process import CommandResult
from legends_ytdlp.tools import ToolInfo


class OptionalVpnTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name in ['ytdlp', 'ffmpeg']:
            self.stack.enter_context(patch('legends_ytdlp.doctor.find_' + name,
                return_value=ToolInfo(name, Path(name), 'test', True, 'ready')))

    def test_ordinary_doctor_does_not_probe_vpn_or_account(self):
        with patch('legends_ytdlp.doctor.find_mullvad') as tool, \
             patch('legends_ytdlp.doctor.mullvad_status') as status, \
             patch('legends_ytdlp.doctor.read_env_file') as account:
            self.assertTrue(overall_ok(run_doctor()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cmd_doctor(argparse.Namespace(production=False, require_connected=False)), 0)
            tool.assert_not_called()
            status.assert_not_called()
            account.assert_not_called()

    def test_explicit_connected_doctor_requires_missing_vpn(self):
        with patch('legends_ytdlp.doctor.find_mullvad', return_value=ToolInfo('mullvad', None, None, False, 'missing')), \
             patch('legends_ytdlp.doctor.mullvad_status', return_value=MullvadStatus(False, False, '', 'missing')), \
             patch('legends_ytdlp.doctor.read_env_file', return_value={}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cmd_doctor(argparse.Namespace(production=False, require_connected=True)), 1)

    def test_production_doctor_still_checks_vpn_posture(self):
        with patch('legends_ytdlp.doctor.find_mullvad', return_value=ToolInfo('mullvad', Path('mullvad'), 'test', True, 'ready')), \
             patch('legends_ytdlp.doctor.mullvad_status', return_value=MullvadStatus(True, True, 'Connected')), \
             patch('legends_ytdlp.doctor.read_env_file', return_value={'MULLVAD_ACCOUNT_NUMBER': 'fixture'}), \
             patch('legends_ytdlp.doctor.find_js_runtime', return_value=ToolInfo('js', Path('node'), 'test', True, 'ready')):
            with contextlib.ExitStack() as stack:
                for name in ['lockdown_setting', 'split_tunnel_setting', 'lan_setting', 'auto_connect_setting']:
                    stack.enter_context(patch('legends_ytdlp.doctor.' + name, return_value=MullvadSetting(True, 'off', 'on')))
                checks = run_doctor(production=True)
                self.assertIn('mullvad lockdown', [check.name for check in checks])
                self.assertFalse(overall_ok(checks, require_connected=True))

    def test_optional_failures_ignored_but_required_tool_failure_preserved(self):
        vpn = [Check(name, False, 'missing') for name in ['mullvad', '.env account', 'mullvad connected', 'mullvad lockdown']]
        self.assertTrue(overall_ok(vpn))
        self.assertFalse(overall_ok(vpn, require_connected=True))
        self.assertFalse(overall_ok(vpn + [Check('yt-dlp', False, 'missing')]))

    def test_default_preflight_and_run_work_without_vpn(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('legends_ytdlp.batch.BATCHES_DIR', Path(tmp) / 'batches'), \
             patch('legends_ytdlp.doctor.find_mullvad') as vpn, \
             patch('legends_ytdlp.doctor.read_env_file') as account, \
             patch('legends_ytdlp.cli.shutdown_connection') as shutdown, \
             patch('legends_ytdlp.cli.recover_connection') as recover:
            paths = create_batch_from_urls(urls=['https://example.com/fixture'], name='no-vpn', output_dir=str(Path(tmp) / 'out'))
            self.assertTrue(preflight_ok(preflight_batch(paths.manifest)))
            args = argparse.Namespace(manifest=str(paths.manifest), with_vpn=False, dry_run=False,
                bulk=False, recover_vpn=True, vpn_recovery_attempts=0, vpn_recovery_wait=0,
                yes=True, show_output=False, keep_vpn=False)
            with patch('legends_ytdlp.cli.run_batch', return_value=CommandResult(('yt-dlp',), 0, '', '')) as download, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cmd_run(args), 0)
                download.assert_called_once()
            vpn.assert_not_called()
            account.assert_not_called()
            recover.assert_not_called()
            shutdown.assert_not_called()


if __name__ == '__main__':
    unittest.main()
