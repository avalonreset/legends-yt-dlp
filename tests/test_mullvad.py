import unittest

from slayer_cli.mullvad import MullvadSetting, MullvadStatus, disconnect_refusal_reason, recovery_action_for_status


class MullvadSettingTests(unittest.TestCase):
    def test_lockdown_off_does_not_match_on_inside_disconnected(self) -> None:
        setting = MullvadSetting(True, "Block traffic when the VPN is disconnected: off", "on")
        self.assertEqual(setting.value, "off")
        self.assertFalse(setting.ok)

    def test_auto_connect_off_does_not_match_on_inside_autoconnect(self) -> None:
        setting = MullvadSetting(True, "Autoconnect: off", "on")
        self.assertEqual(setting.value, "off")
        self.assertFalse(setting.ok)

    def test_expected_value_passes(self) -> None:
        setting = MullvadSetting(True, "Local network sharing setting: block", "block")
        self.assertTrue(setting.ok)


class RecoveryActionTests(unittest.TestCase):
    def test_disconnect_refuses_when_lockdown_on(self) -> None:
        setting = MullvadSetting(True, "Block traffic when the VPN is disconnected: on", "on")
        self.assertIn("Lockdown is on", disconnect_refusal_reason(setting))

    def test_disconnect_allows_force_when_lockdown_on(self) -> None:
        setting = MullvadSetting(True, "Block traffic when the VPN is disconnected: on", "on")
        self.assertIsNone(disconnect_refusal_reason(setting, force=True))

    def test_disconnect_refuses_when_lockdown_unknown(self) -> None:
        setting = MullvadSetting(False, "unavailable", "on")
        self.assertIn("could not be verified", disconnect_refusal_reason(setting))

    def test_disconnect_allows_when_lockdown_off(self) -> None:
        setting = MullvadSetting(True, "Block traffic when the VPN is disconnected: off", "on")
        self.assertIsNone(disconnect_refusal_reason(setting))

    def test_disconnected_status_uses_connect(self) -> None:
        status = MullvadStatus(True, False, "Disconnected")
        self.assertEqual(recovery_action_for_status(status), "connect")

    def test_disconnect_transition_uses_connect(self) -> None:
        status = MullvadStatus(True, False, "Disconnecting")
        self.assertEqual(recovery_action_for_status(status), "connect")

    def test_unavailable_status_uses_connect(self) -> None:
        status = MullvadStatus(False, False, "", "mullvad status failed")
        self.assertEqual(recovery_action_for_status(status), "connect")

    def test_connecting_status_uses_reconnect(self) -> None:
        status = MullvadStatus(True, False, "Connecting to us-nyc-wg-101...")
        self.assertEqual(recovery_action_for_status(status), "reconnect")


if __name__ == "__main__":
    unittest.main()
