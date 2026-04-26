from __future__ import annotations

import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from player.preferences.models import AppSettings


class AppSettingsTests(unittest.TestCase):
    def test_audio_output_device_id_round_trips(self):
        settings = AppSettings(audio_output_device_id="wasapi/{device-1}")

        payload = settings.to_dict()
        restored_settings = AppSettings.from_dict(payload)

        self.assertEqual(payload["audio_output_device_id"], "wasapi/{device-1}")
        self.assertEqual(restored_settings.audio_output_device_id, "wasapi/{device-1}")


if __name__ == "__main__":
    unittest.main()