import wx

from ..accessibility import ScreenReaderAnnouncer
from ..constants import APP_TITLE, DEFAULT_WINDOW_SIZE
from ..preferences import load_settings, save_settings
from .commands import FrameCommandMixin
from .equalizer import FrameEqualizerMixin
from .library import FrameLibraryMixin
from .playback import FramePlaybackMixin
from .recents import FrameRecentsMixin
from .session import FrameSessionMixin
from .ui import FrameUIMixin
from .update import FrameUpdateMixin
from .youtube_music import FrameYouTubeMusicMixin


class VLCPlayerFrame(
    FrameYouTubeMusicMixin,
    FrameCommandMixin,
    FrameSessionMixin,
    FrameRecentsMixin,
    FrameEqualizerMixin,
    FrameLibraryMixin,
    FramePlaybackMixin,
    FrameUpdateMixin,
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
        self._startup_update_check_scheduled = False
        self._update_check_in_progress = False
        self._update_restart_pending = False

        self._create_player_backend()
        self._create_library_loader()

        self._build_menu_bar()
        self._build_ui()
        self._bind_events()
        self._refresh_youtube_music_menu_state()

        self.Centre()
        self.Show()
        wx.CallAfter(self._initialize_player_state)
        wx.CallAfter(self._verify_youtube_music_connection)
        wx.CallAfter(self._prime_equalizer_ui)
        wx.CallAfter(self._schedule_startup_update_check)

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
