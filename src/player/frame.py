import wx

from .accessibility import ScreenReaderAnnouncer
from .constants import APP_TITLE, DEFAULT_WINDOW_SIZE
from .frame_commands import FrameCommandMixin
from .frame_equalizer import FrameEqualizerMixin
from .frame_library import FrameLibraryMixin
from .frame_playback import FramePlaybackMixin
from .frame_recents import FrameRecentsMixin
from .frame_session import FrameSessionMixin
from .frame_ui import FrameUIMixin
from .settings import load_settings, save_settings


class VLCPlayerFrame(
    FrameCommandMixin,
    FrameSessionMixin,
    FrameRecentsMixin,
    FrameEqualizerMixin,
    FrameLibraryMixin,
    FramePlaybackMixin,
    FrameUIMixin,
    wx.Frame,
):
    def __init__(self):
        super().__init__(None, title=APP_TITLE, size=DEFAULT_WINDOW_SIZE)

        self.settings = load_settings()
        self._initialize_equalizer_support()
        self.current_volume = self.settings.default_volume
        self.playlists = []
        self.active_playlist_index = None
        self.announcer = ScreenReaderAnnouncer()
        self._suppress_tab_change_event = False
        self._recent_menu_actions = {}
        self._recent_menu_ids = []

        self._create_player_backend()

        self._build_menu_bar()
        self._build_ui()
        self._bind_events()

        self.Centre()
        self.Show()
        wx.CallAfter(self._initialize_player_state)
        wx.CallAfter(self._prime_equalizer_ui)

    def _announce(self, message):
        if not self.settings.announcements_enabled:
            return
        self.announcer.speak(message)

    def _save_settings(self):
        try:
            save_settings(self.settings)
        except OSError:
            return False
        return True
