from __future__ import annotations

import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from player import mpv_backend


class _FakePlayerCore:
    def __init__(self):
        self.pause = False
        self.volume = 100
        self.time_pos = 0
        self.duration = 180
        self.wid = None
        self.core_idle = True
        self.loaded = []
        self.stopped = 0
        self.terminated = 0
        self.callbacks = {}

    def event_callback(self, *event_names):
        def decorator(callback):
            for event_name in event_names:
                self.callbacks[event_name] = callback
            return callback

        return decorator

    def loadfile(self, path, mode):
        self.loaded.append((path, mode))
        self.core_idle = False

    def stop(self):
        self.stopped += 1
        self.core_idle = True

    def terminate(self):
        self.terminated += 1

    def __setitem__(self, key, value):
        setattr(self, key, value)


class _FakeMPVModule:
    class MpvEventEndFile:
        ERROR = "error"
        EOF = "eof"

    def __init__(self):
        self.created_players = []

    def MPV(self, **_kwargs):
        player = _FakePlayerCore()
        self.created_players.append(player)
        return player


class MPVPlayerTests(unittest.TestCase):
    def setUp(self):
        self._previous_module = mpv_backend._mpv_module
        self.fake_module = _FakeMPVModule()
        mpv_backend._mpv_module = self.fake_module

    def tearDown(self):
        mpv_backend._mpv_module = self._previous_module

    def test_resume_after_pause_does_not_reload_media(self):
        player = mpv_backend.MPVPlayer(video_output_enabled=False)
        media = mpv_backend.MPVMedia(path="song.mp3")
        player.set_media(media)

        player.play()
        core = self.fake_module.created_players[0]
        self.assertEqual(core.loaded, [("song.mp3", "replace")])

        player.pause()
        core.core_idle = True

        player.play()

        self.assertEqual(core.loaded, [("song.mp3", "replace")])
        self.assertFalse(core.pause)

    def test_replay_after_stop_still_reloads_media(self):
        player = mpv_backend.MPVPlayer(video_output_enabled=False)
        media = mpv_backend.MPVMedia(path="song.mp3")
        player.set_media(media)

        player.play()
        core = self.fake_module.created_players[0]

        player.stop()
        player.play()

        self.assertEqual(core.loaded, [("song.mp3", "replace"), ("song.mp3", "replace")])


if __name__ == "__main__":
    unittest.main()