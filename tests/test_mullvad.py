import unittest

from slayer_cli.mullvad import MullvadSetting


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


if __name__ == "__main__":
    unittest.main()
