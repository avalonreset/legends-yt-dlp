import json
import unittest

from slayer_cli.doctor import Check
from slayer_cli.onboarding import next_setup_steps, onboarding_json, onboarding_text, readiness_summary


class OnboardingTests(unittest.TestCase):
    def test_onboarding_reports_missing_setup_steps(self) -> None:
        checks = [
            Check("mullvad", False, "missing"),
            Check("yt-dlp", False, "missing"),
            Check("ffmpeg", True, "ok"),
            Check(".env account", False, "missing"),
            Check("mullvad connected", False, "not connected"),
            Check("yt-dlp JS runtime", False, "missing"),
            Check("mullvad lockdown", False, "off"),
        ]

        steps = next_setup_steps(checks)
        text = onboarding_text(checks)

        self.assertEqual(readiness_summary(checks), "ACTION REQUIRED")
        self.assertTrue(any("Install Mullvad VPN" in step for step in steps))
        self.assertIn("yt-dlp install", "\n".join(steps))
        self.assertIn("setup production", "\n".join(steps))
        self.assertIn("Ask the user these before a real batch", text)
        self.assertIn("Safety boundary", text)

    def test_onboarding_ready_state_shows_first_smoke_flow(self) -> None:
        checks = [
            Check("mullvad", True, "ok"),
            Check("yt-dlp", True, "ok"),
            Check("ffmpeg", True, "ok"),
            Check(".env account", True, "present"),
            Check("mullvad connected", True, "connected"),
            Check("yt-dlp JS runtime", True, "ok"),
            Check("mullvad lockdown", True, "on"),
            Check("mullvad split tunnel off", True, "off"),
            Check("mullvad LAN sharing blocked", True, "blocked"),
            Check("mullvad auto-connect", True, "on"),
        ]

        payload = json.loads(onboarding_json(checks))
        text = onboarding_text(checks)

        self.assertEqual(payload["status"], "READY")
        self.assertIn("smoke plan --count 1", "\n".join(payload["next_steps"]))
        self.assertIn("Normal first batch flow", text)
        self.assertIn("inventory", text)


if __name__ == "__main__":
    unittest.main()
