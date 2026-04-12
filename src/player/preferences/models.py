from dataclasses import dataclass, field

from ..constants import (
    DEFAULT_ANNOUNCEMENTS_ENABLED,
    DEFAULT_CONFIRM_ON_EXIT,
    DEFAULT_CROSSFADE_SECONDS,
    DEFAULT_NEW_PLAYLIST_SHUFFLE,
    DEFAULT_REMEMBER_LAST_FOLDER,
    DEFAULT_REMEMBER_WINDOW_SIZE,
    DEFAULT_RESTORE_SESSION_ON_STARTUP,
    DEFAULT_VOLUME,
    MAX_CROSSFADE_SECONDS,
    REPEAT_MODES,
    REPEAT_OFF,
    SEEK_STEP_MS,
    VOLUME_STEP,
)
from ..equalizer import EqualizerPreset


@dataclass
class AppSettings:
    restore_session_on_startup: bool = DEFAULT_RESTORE_SESSION_ON_STARTUP
    remember_window_size: bool = DEFAULT_REMEMBER_WINDOW_SIZE
    remember_last_folder: bool = DEFAULT_REMEMBER_LAST_FOLDER
    confirm_on_exit: bool = DEFAULT_CONFIRM_ON_EXIT
    announcements_enabled: bool = DEFAULT_ANNOUNCEMENTS_ENABLED
    default_volume: int = DEFAULT_VOLUME
    crossfade_seconds: int = DEFAULT_CROSSFADE_SECONDS
    volume_step: int = VOLUME_STEP
    seek_step_seconds: int = SEEK_STEP_MS // 1000
    shuffle_new_playlists: bool = DEFAULT_NEW_PLAYLIST_SHUFFLE
    repeat_mode_new_playlists: str = REPEAT_OFF
    last_open_dir: str = ""
    recent_media_files: list[str] = field(default_factory=list)
    recent_folders: list[str] = field(default_factory=list)
    recent_playlists: list[str] = field(default_factory=list)
    equalizer_custom_presets: list[EqualizerPreset] = field(default_factory=list)

    @property
    def seek_step_ms(self):
        return self.seek_step_seconds * 1000

    def to_dict(self):
        return {
            "restore_session_on_startup": self.restore_session_on_startup,
            "remember_window_size": self.remember_window_size,
            "remember_last_folder": self.remember_last_folder,
            "confirm_on_exit": self.confirm_on_exit,
            "announcements_enabled": self.announcements_enabled,
            "default_volume": self.default_volume,
            "crossfade_seconds": self.crossfade_seconds,
            "volume_step": self.volume_step,
            "seek_step_seconds": self.seek_step_seconds,
            "shuffle_new_playlists": self.shuffle_new_playlists,
            "repeat_mode_new_playlists": self.repeat_mode_new_playlists,
            "last_open_dir": self.last_open_dir if self.remember_last_folder else "",
            "recent_media_files": list(self.recent_media_files),
            "recent_folders": list(self.recent_folders),
            "recent_playlists": list(self.recent_playlists),
            "equalizer_custom_presets": [preset.to_dict() for preset in self.equalizer_custom_presets],
        }

    @classmethod
    def from_dict(cls, data):
        settings = cls()
        settings.restore_session_on_startup = bool(data.get("restore_session_on_startup", settings.restore_session_on_startup))
        settings.remember_window_size = bool(data.get("remember_window_size", settings.remember_window_size))
        settings.remember_last_folder = bool(data.get("remember_last_folder", settings.remember_last_folder))
        settings.confirm_on_exit = bool(data.get("confirm_on_exit", settings.confirm_on_exit))
        settings.announcements_enabled = bool(data.get("announcements_enabled", settings.announcements_enabled))
        settings.default_volume = _clamp_int(data.get("default_volume"), minimum=0, maximum=100, fallback=settings.default_volume)
        settings.crossfade_seconds = _clamp_int(
            data.get("crossfade_seconds"),
            minimum=0,
            maximum=MAX_CROSSFADE_SECONDS,
            fallback=settings.crossfade_seconds,
        )
        settings.volume_step = _clamp_int(data.get("volume_step"), minimum=1, maximum=25, fallback=settings.volume_step)
        settings.seek_step_seconds = _clamp_int(
            data.get("seek_step_seconds"),
            minimum=1,
            maximum=120,
            fallback=settings.seek_step_seconds,
        )
        settings.shuffle_new_playlists = bool(data.get("shuffle_new_playlists", settings.shuffle_new_playlists))

        repeat_mode = data.get("repeat_mode_new_playlists", settings.repeat_mode_new_playlists)
        settings.repeat_mode_new_playlists = repeat_mode if repeat_mode in REPEAT_MODES else REPEAT_OFF

        last_open_dir = str(data.get("last_open_dir") or "").strip()
        settings.last_open_dir = last_open_dir if settings.remember_last_folder else ""
        settings.recent_media_files = _string_list(data.get("recent_media_files"))
        settings.recent_folders = _string_list(data.get("recent_folders"))
        settings.recent_playlists = _string_list(data.get("recent_playlists"))
        settings.equalizer_custom_presets = _equalizer_preset_list(data.get("equalizer_custom_presets"))
        return settings


def _clamp_int(value, minimum, maximum, fallback):
    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return fallback

    return max(minimum, min(maximum, numeric_value))


def _string_list(value):
    if not isinstance(value, list):
        return []

    normalized_items = []
    for item in value:
        normalized_item = str(item or "").strip()
        if normalized_item:
            normalized_items.append(normalized_item)

    return normalized_items


def _equalizer_preset_list(value):
    if not isinstance(value, list):
        return []

    presets = []
    for item in value:
        if not isinstance(item, dict):
            continue
        presets.append(EqualizerPreset.from_dict(item))

    return presets
