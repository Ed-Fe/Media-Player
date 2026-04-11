import os
import random
from dataclasses import dataclass, field

from .constants import REPEAT_MODES, REPEAT_OFF


TAB_TYPE_PLAYLIST = "playlist"
TAB_TYPE_FOLDER = "folder"


def default_playlist_title(number):
    return f"Playlist {number}"


def build_playlist_title(items, explicit_title=None):
    if explicit_title:
        return explicit_title

    normalized_items = list(items)
    if not normalized_items:
        return default_playlist_title(1)

    if len(normalized_items) == 1:
        return os.path.splitext(os.path.basename(normalized_items[0]))[0]

    parent_directories = {os.path.dirname(path) for path in normalized_items}
    if len(parent_directories) == 1:
        folder_name = os.path.basename(parent_directories.pop())
        if folder_name:
            return f"{folder_name} ({len(normalized_items)})"

    return f"Seleção ({len(normalized_items)})"


def build_folder_tab_title(folder_path):
    normalized_path = os.path.abspath(os.path.normpath(str(folder_path or "")))
    folder_name = os.path.basename(normalized_path.rstrip("\\/")) or normalized_path
    return f"Pasta: {folder_name}"


@dataclass
class PlaylistState:
    title: str
    items: list[str] = field(default_factory=list)
    current_index: int = -1
    current_media_path: str | None = None
    last_position_ms: int = 0
    was_playing: bool = False
    source_path: str | None = None
    shuffle_enabled: bool = False
    repeat_mode: str = REPEAT_OFF
    playback_order: list[int] = field(default_factory=list)
    playback_order_position: int = 0
    tab_type: str = TAB_TYPE_PLAYLIST
    folder_root_path: str | None = None
    folder_current_path: str | None = None
    folder_selected_path: str | None = None
    folder_entries: list = field(default_factory=list)

    @property
    def is_empty(self):
        return not self.is_folder_tab and not self.items and not self.current_media_path

    @property
    def is_folder_tab(self):
        return self.tab_type == TAB_TYPE_FOLDER

    @property
    def item_count(self):
        return len(self.items)

    def clear(self):
        self.items = []
        self.current_index = -1
        self.current_media_path = None
        self.last_position_ms = 0
        self.was_playing = False
        self.playback_order = []
        self.playback_order_position = 0

    def set_items(self, items, start_index=0, auto_select=True):
        self.items = list(items)
        if not self.items:
            self.current_index = -1
            self.current_media_path = None
            self.last_position_ms = 0
            self.was_playing = False
            self.playback_order = []
            self.playback_order_position = 0
            return

        if auto_select:
            self.select_index(start_index)
        else:
            self.current_index = -1
            self.current_media_path = None
            self.last_position_ms = 0
            self.was_playing = False
            self.reset_playback_order(preferred_index=0)

    def set_folder_location(self, root_path, current_path=None, selected_path=None):
        normalized_root_path = os.path.abspath(os.path.normpath(str(root_path or "")))
        normalized_current_path = current_path or normalized_root_path
        normalized_current_path = os.path.abspath(os.path.normpath(str(normalized_current_path or normalized_root_path)))

        self.tab_type = TAB_TYPE_FOLDER
        self.folder_root_path = normalized_root_path
        self.folder_current_path = normalized_current_path
        self.folder_selected_path = str(selected_path or "").strip() or None
        self.folder_entries = []

    def clear_folder_location(self):
        self.tab_type = TAB_TYPE_PLAYLIST
        self.folder_root_path = None
        self.folder_current_path = None
        self.folder_selected_path = None
        self.folder_entries = []

    def set_folder_entries(self, entries):
        self.folder_entries = list(entries)

    def set_current_media_path(self, media_path):
        if not self.items or media_path not in self.items:
            self.current_index = -1
            self.current_media_path = None
            self.last_position_ms = 0
            self.was_playing = False
            self.sync_playback_order()
            return None

        return self.select_index(self.items.index(media_path))

    def select_index(self, index, reset_playback_order=True):
        if not self.items:
            self.clear()
            return None

        bounded_index = max(0, min(index, len(self.items) - 1))
        self.current_index = bounded_index
        self.current_media_path = self.items[bounded_index]
        self.last_position_ms = 0

        if reset_playback_order:
            self.reset_playback_order(preferred_index=bounded_index)
        else:
            self.sync_playback_order()

        return self.current_media_path

    def current_item_name(self):
        if not self.current_media_path:
            return None
        return os.path.basename(self.current_media_path)

    def has_next(self):
        return self.current_index + 1 < len(self.items)

    def has_previous(self):
        return self.current_index > 0

    def move_next(self):
        return self.move_in_playback_order(1)

    def move_previous(self):
        return self.move_in_playback_order(-1)

    def reset_playback_order(self, preferred_index=None, anchor_current=True):
        if not self.items:
            self.playback_order = []
            self.playback_order_position = 0
            return

        if preferred_index is None or not 0 <= preferred_index < len(self.items):
            preferred_index = self.current_index if 0 <= self.current_index < len(self.items) else 0

        if not self.shuffle_enabled:
            self.playback_order = list(range(len(self.items)))
            self.playback_order_position = preferred_index
            return

        ordered_indices = list(range(len(self.items)))
        if anchor_current and preferred_index in ordered_indices:
            ordered_indices.remove(preferred_index)
            random.shuffle(ordered_indices)
            ordered_indices.insert(0, preferred_index)
            self.playback_order = ordered_indices
            self.playback_order_position = 0
            return

        random.shuffle(ordered_indices)
        self.playback_order = ordered_indices
        self.playback_order_position = (
            ordered_indices.index(preferred_index) if preferred_index in ordered_indices else 0
        )

    def sync_playback_order(self):
        if not self.items:
            self.playback_order = []
            self.playback_order_position = 0
            return

        expected_indices = set(range(len(self.items)))
        current_indices = set(self.playback_order)

        if len(self.playback_order) != len(self.items) or current_indices != expected_indices:
            self.reset_playback_order(preferred_index=self.current_index)
            return

        if self.current_index in self.playback_order:
            self.playback_order_position = self.playback_order.index(self.current_index)

    def move_in_playback_order(self, direction, wrap=False):
        if not self.items:
            return None

        self.sync_playback_order()

        if not self.shuffle_enabled:
            target_index = self.current_index + direction
            if wrap:
                target_index %= len(self.items)
            elif not 0 <= target_index < len(self.items):
                return None

            return self.select_index(target_index, reset_playback_order=False)

        target_position = self.playback_order_position + direction
        if 0 <= target_position < len(self.playback_order):
            self.playback_order_position = target_position
            return self.select_index(self.playback_order[target_position], reset_playback_order=False)

        if not wrap:
            return None

        if direction < 0:
            self.playback_order_position = len(self.playback_order) - 1
            return self.select_index(self.playback_order[self.playback_order_position], reset_playback_order=False)

        self.reset_playback_order(preferred_index=self.current_index, anchor_current=False)
        if not self.playback_order:
            return None

        self.playback_order_position = 0
        return self.select_index(self.playback_order[0], reset_playback_order=False)

    def to_dict(self):
        return {
            "title": self.title,
            "items": list(self.items),
            "current_index": self.current_index,
            "current_media_path": self.current_media_path,
            "last_position_ms": self.last_position_ms,
            "was_playing": self.was_playing,
            "source_path": self.source_path,
            "shuffle_enabled": self.shuffle_enabled,
            "repeat_mode": self.repeat_mode,
            "tab_type": self.tab_type,
            "folder_root_path": self.folder_root_path,
            "folder_current_path": self.folder_current_path,
            "folder_selected_path": self.folder_selected_path,
        }

    @classmethod
    def from_dict(cls, data):
        items = [str(item) for item in data.get("items", []) if item]
        title = str(data.get("title") or build_playlist_title(items))
        state = cls(title=title)
        state.items = items
        state.source_path = data.get("source_path")
        state.shuffle_enabled = bool(data.get("shuffle_enabled", False))
        tab_type = data.get("tab_type", TAB_TYPE_PLAYLIST)
        state.tab_type = tab_type if tab_type in {TAB_TYPE_PLAYLIST, TAB_TYPE_FOLDER} else TAB_TYPE_PLAYLIST
        state.folder_root_path = data.get("folder_root_path") or None
        state.folder_current_path = data.get("folder_current_path") or None
        state.folder_selected_path = data.get("folder_selected_path") or None

        repeat_mode = data.get("repeat_mode", REPEAT_OFF)
        state.repeat_mode = repeat_mode if repeat_mode in REPEAT_MODES else REPEAT_OFF

        current_media_path = data.get("current_media_path")
        current_index = data.get("current_index", -1)

        if items:
            if current_media_path in items:
                state.current_index = items.index(current_media_path)
                state.current_media_path = current_media_path
            elif isinstance(current_index, int) and 0 <= current_index < len(items):
                state.current_index = current_index
                state.current_media_path = items[current_index]
            else:
                state.current_index = 0
                state.current_media_path = items[0]
        else:
            state.current_index = -1
            state.current_media_path = None

        try:
            state.last_position_ms = max(0, int(data.get("last_position_ms", 0)))
        except (TypeError, ValueError):
            state.last_position_ms = 0

        state.was_playing = bool(data.get("was_playing", False))
        state.reset_playback_order(preferred_index=state.current_index if state.current_index >= 0 else 0)
        return state
