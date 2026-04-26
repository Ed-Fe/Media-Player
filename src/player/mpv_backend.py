from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


_mpv_module = None


def _load_mpv_module():
    global _mpv_module
    if _mpv_module is None:
        _mpv_module = importlib.import_module("mpv")
    return _mpv_module


class PlayerEventType(Enum):
    MEDIA_PLAYER_END_REACHED = "media-player-end-reached"
    MEDIA_PLAYER_PLAYING = "media-player-playing"
    MEDIA_PLAYER_ERROR = "media-player-error"


@dataclass(slots=True)
class MPVMedia:
    path: str


class MPVEventManager:
    def __init__(self):
        self._callbacks: dict[PlayerEventType, list[tuple[Callable[..., Any], tuple[Any, ...]]]] = {
            event_type: [] for event_type in PlayerEventType
        }

    def event_attach(self, event_type: PlayerEventType, callback: Callable[..., Any], *args: Any):
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append((callback, args))

    def emit(self, event_type: PlayerEventType, event: Any = None):
        for callback, args in list(self._callbacks.get(event_type, [])):
            try:
                callback(event, *args)
            except Exception:
                continue


class MPVPlayer:
    def __init__(self, *, video_output_enabled: bool = True):
        self._mpv = _load_mpv_module()
        self._event_manager = MPVEventManager()
        self._media: MPVMedia | None = None
        self._loaded_media_path: str | None = None
        self._needs_load = False
        self._bound_handle: str | None = None
        self._bound_video_output = video_output_enabled
        self._last_end_reason: int | None = None
        player_kwargs = {
            "input_default_bindings": False,
            "input_vo_keyboard": False,
            "osc": False,
            "keep_open": "yes",
        }
        if not video_output_enabled:
            player_kwargs["video"] = False
        try:
            self._player = self._mpv.MPV(**player_kwargs)
        except Exception as exc:
            raise RuntimeError(
                "Não foi possível carregar o runtime do MPV. "
                "Verifique se a pasta mpv/ está disponível ao lado do app ou se o runtime do MPV foi instalado no sistema."
            ) from exc
        self._register_callbacks()

    def _core_is_idle(self):
        try:
            return bool(self._player.core_idle)
        except Exception:
            return True

    def _register_callbacks(self):
        end_file_enum = getattr(self._mpv, "MpvEventEndFile", None)
        error_reason = getattr(end_file_enum, "ERROR", None)
        eof_reason = getattr(end_file_enum, "EOF", None)

        @self._player.event_callback("end-file")
        def _on_end_file(event):
            end_event = getattr(event, "data", None)
            reason = getattr(end_event, "reason", None)
            self._last_end_reason = reason
            if error_reason is not None and reason == error_reason:
                self._loaded_media_path = None
                self._needs_load = True
                self._event_manager.emit(PlayerEventType.MEDIA_PLAYER_ERROR, event)
                return
            if eof_reason is not None and reason == eof_reason:
                self._needs_load = True
                self._event_manager.emit(PlayerEventType.MEDIA_PLAYER_END_REACHED, event)

        @self._player.event_callback("file-loaded", "playback-restart")
        def _on_playback_event(event):
            self._needs_load = False
            self._loaded_media_path = self._media.path if self._media else self._loaded_media_path
            self._event_manager.emit(PlayerEventType.MEDIA_PLAYER_PLAYING, event)

    def event_manager(self):
        return self._event_manager

    def video_set_key_input(self, _enabled):
        return None

    def video_set_mouse_input(self, _enabled):
        return None

    def set_hwnd(self, handle):
        self._set_window_handle(handle)

    def set_xwindow(self, handle):
        self._set_window_handle(handle)

    def set_nsobject(self, handle):
        self._set_window_handle(handle)

    def _set_window_handle(self, handle):
        if not self._bound_video_output:
            return
        try:
            normalized_handle = str(int(handle))
        except (TypeError, ValueError):
            return
        self._bound_handle = normalized_handle
        try:
            self._player.wid = normalized_handle
        except Exception:
            try:
                self._player["wid"] = normalized_handle
            except Exception:
                return

    def set_media(self, media: MPVMedia | None):
        self._media = media
        self._loaded_media_path = None
        self._needs_load = media is not None

    def get_media(self):
        return self._media

    def play(self):
        if self._media is None:
            return
        if self._bound_handle and self._bound_video_output:
            self._set_window_handle(self._bound_handle)
        if self._needs_load or self._loaded_media_path != self._media.path:
            self._player.pause = False
            self._player.loadfile(self._media.path, "replace")
            self._loaded_media_path = self._media.path
            self._needs_load = False
            return
        self._player.pause = False

    def pause(self):
        self._player.pause = True

    def stop(self):
        try:
            self._player.stop()
        finally:
            self._needs_load = self._media is not None

    def release(self):
        try:
            self._player.stop()
        except Exception:
            pass
        self._player.terminate()

    def is_playing(self):
        try:
            return not bool(self._player.pause) and not self._core_is_idle()
        except Exception:
            return False

    def audio_set_volume(self, volume):
        self._player.volume = max(0, min(100, int(volume)))

    def get_time(self):
        time_pos = self._player.time_pos
        if time_pos is None:
            return -1
        return int(round(float(time_pos) * 1000))

    def get_length(self):
        duration = self._player.duration
        if duration is None:
            return -1
        return int(round(float(duration) * 1000))

    def set_time(self, milliseconds):
        self._player.time_pos = max(0.0, float(milliseconds) / 1000.0)

    def set_position(self, position):
        percentage = max(0.0, min(1.0, float(position))) * 100.0
        self._player.percent_pos = percentage

    def set_audio_filters(self, filter_chain: str):
        self._player["af"] = filter_chain or ""


class MPVInstance:
    def __init__(self, *, video_output_enabled: bool = True):
        self._video_output_enabled = video_output_enabled

    def media_player_new(self):
        return MPVPlayer(video_output_enabled=self._video_output_enabled)

    def media_new(self, media_path):
        return MPVMedia(path=str(media_path or "").strip())

    def release(self):
        return None


def create_player_instance(*, video_output_enabled: bool = True):
    return MPVInstance(video_output_enabled=video_output_enabled)
