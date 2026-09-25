import unittest
from pathlib import Path

from legends_ytdlp.envfile import read_env_file, redact


class EnvFileTests(unittest.TestCase):
    def test_read_env_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("A=1\n# ignored\nB=\"two\"\n\n", encoding="utf-8")
            self.assertEqual(read_env_file(env), {"A": "1", "B": "two"})

    def test_redact_keeps_tail(self) -> None:
        self.assertEqual(redact("1234567890"), "******7890")
        self.assertEqual(redact(None), "<missing>")

