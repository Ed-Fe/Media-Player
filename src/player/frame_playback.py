import os
import sys

import vlc
import wx

from .constants import PROGRESS_GAUGE_RANGE
from .media import folder_display_name


class FramePlaybackMixin:
    def _initialize_player_state(self):
        self._bind_player_to_window()
        if self.settings.restore_session_on_startup and self._restore_session():
            return

        self._update_title()
        self._announce("Nenhuma mídia tocando agora.")

    def _create_player_backend(self):
        self.instance = self._build_vlc_instance()
        self.player = self.instance.media_player_new()
        self._event_manager = self.player.event_manager()
        self._event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end_reached)

    def _build_vlc_instance(self):
        args = ["--quiet"]
        if sys.platform.startswith("linux"):
            args.append("--no-xlib")
        return vlc.Instance(*args)

    def _on_media_end_reached(self, _event):
        wx.CallAfter(self._handle_media_end)

    def _unload_player(self):
        self.player.stop()
        try:
            self.player.set_media(None)
            self._bind_player_to_window()
        except Exception:
            self._reset_player()
        self._update_time_bar()

    def _bind_player_to_window(self):
        video_panel = self._get_video_panel()
        if not video_panel:
            return

        handle = video_panel.GetHandle()
        if not handle:
            return

        if sys.platform.startswith("win"):
            self.player.set_hwnd(handle)
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(handle)
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(handle))

    def _load_media(self, media_path):
        media = self.instance.media_new(media_path)
        self.player.set_media(media)
        self._update_title()
        self._update_time_bar()

    def _media_label(self, media_path):
        if not media_path:
            return "Sem mídia"

        normalized_path = str(media_path).rstrip("\\/")
        media_name = os.path.basename(normalized_path)
        return media_name or normalized_path

    def _format_time_ms(self, milliseconds):
        if milliseconds is None or milliseconds < 0:
            return "tempo desconhecido"

        total_seconds = int(milliseconds // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02}:{seconds:02}"
        return f"{minutes}:{seconds:02}"

    def _time_bar_accessible_value(self):
        return self.progress_label.GetLabel()

    def _update_time_bar(self):
        if not hasattr(self, "progress_label") or not hasattr(self, "progress_gauge"):
            return

        media = self.player.get_media() if hasattr(self, "player") else None
        if media is None:
            self.progress_label.SetLabel("Tempo: nenhuma mídia carregada.")
            self.progress_gauge.SetValue(0)
            return

        current_time = self.player.get_time()
        if current_time is None or current_time < 0:
            current_time = 0

        total_time = self.player.get_length()
        current_label = self._format_time_ms(current_time)

        if total_time is None or total_time <= 0:
            self.progress_label.SetLabel(f"Tempo: {current_label} / duração desconhecida")
            if self.player.is_playing():
                self.progress_gauge.Pulse()
            else:
                self.progress_gauge.SetValue(0)
            return

        bounded_current_time = max(0, min(current_time, total_time))
        percentage = int(round((bounded_current_time / total_time) * 100)) if total_time > 0 else 0
        gauge_value = int(round((bounded_current_time / total_time) * PROGRESS_GAUGE_RANGE)) if total_time > 0 else 0
        total_label = self._format_time_ms(total_time)

        self.progress_label.SetLabel(f"Tempo: {current_label} / {total_label} ({percentage}%)")
        self.progress_gauge.SetValue(max(0, min(PROGRESS_GAUGE_RANGE, gauge_value)))

    def _seek_relative(self, delta_ms):
        if self.player.get_media() is None:
            return

        current_time = self.player.get_time()
        if current_time is None or current_time < 0:
            current_time = 0

        target_time = max(0, current_time + delta_ms)
        self.player.set_time(target_time)
        self._update_time_bar()

    def _change_volume(self, delta):
        self.current_volume = max(0, min(100, self.current_volume + delta))
        self.player.audio_set_volume(self.current_volume)

    def _seek_to_start(self):
        if self.player.get_media() is None:
            return

        self.player.set_time(0)
        self._update_time_bar()
        self._announce("Início do arquivo.")

    def _seek_to_end(self):
        if self.player.get_media() is None:
            return

        media_length = self.player.get_length()
        if media_length is None or media_length <= 0:
            self.player.set_position(0.99)
        else:
            self.player.set_time(max(0, media_length - 1000))

        self._update_time_bar()
        self._announce("Fim do arquivo.")

    def _reset_player(self):
        try:
            self.player.release()
        except Exception:
            pass

        self.player = self.instance.media_player_new()
        self.player.audio_set_volume(self.current_volume)
        self._event_manager = self.player.event_manager()
        self._event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end_reached)
        self._bind_player_to_window()
        self._update_time_bar()

    def _toggle_play_pause(self):
        state = self._get_playlist_state()
        if not self.player.get_media():
            self.on_open(None)
            return

        if self.player.is_playing():
            self.player.pause()
            if state:
                state.was_playing = False
            self._update_time_bar()
            self._announce("Pausado.")
        else:
            self._bind_player_to_window()
            self.player.play()
            if state:
                state.was_playing = True
            self._update_time_bar()
            self._announce("Reprodução retomada.")

    def _announce_playback_time(self):
        if not self.player.get_media():
            self._announce("Nenhuma mídia carregada.")
            return

        current_time = self.player.get_time()
        if current_time is None or current_time < 0:
            current_time = 0

        total_time = self.player.get_length()
        current_label = self._format_time_ms(current_time)

        if total_time is None or total_time <= 0:
            self._announce(f"Tempo atual: {current_label}.")
            return

        total_label = self._format_time_ms(total_time)
        percentage = int(max(0, min(100, round((max(0, current_time) / total_time) * 100)))) if total_time > 0 else 0
        self._announce(f"Tempo atual: {current_label} de {total_label}. {percentage}%.")

    def _announce_current_volume(self):
        self._announce(f"Volume atual: {self.current_volume}%.")

    def _announce_player_status(self):
        state = self._get_playlist_state()
        status_parts = []

        if state:
            status_parts.append(f"Aba atual: {state.title}.")
            if state.is_folder_tab and state.folder_current_path:
                status_parts.append(f"Pasta atual: {folder_display_name(state.folder_current_path)}.")

        media_path = state.current_media_path if state else None
        if not media_path:
            status_parts.append("Nenhuma mídia tocando agora.")
            status_parts.append(f"Volume atual: {self.current_volume}%.")
            if state:
                shuffle_label = "ligado" if state.shuffle_enabled else "desligado"
                status_parts.append(f"Aleatório {shuffle_label}.")
                status_parts.append(self._repeat_mode_message(state.repeat_mode) + ".")
            self._announce(" ".join(status_parts))
            return

        media_name = self._media_label(media_path)
        playback_state = "tocando" if self.player.is_playing() else "pausado"
        status_parts.append(f"Mídia: {media_name}. Estado: {playback_state}.")

        if state and state.item_count > 0:
            status_parts.append(f"Item {state.current_index + 1} de {state.item_count}.")
            shuffle_label = "ligado" if state.shuffle_enabled else "desligado"
            status_parts.append(f"Aleatório {shuffle_label}.")
            status_parts.append(self._repeat_mode_message(state.repeat_mode) + ".")

        current_time = self.player.get_time()
        if current_time is None or current_time < 0:
            current_time = 0

        total_time = self.player.get_length()
        if total_time is not None and total_time > 0:
            percentage = int(max(0, min(100, round((current_time / total_time) * 100))))
            status_parts.append(
                f"Tempo {self._format_time_ms(current_time)} de {self._format_time_ms(total_time)}. {percentage}%."
            )
        else:
            status_parts.append(f"Tempo atual: {self._format_time_ms(current_time)}.")

        status_parts.append(f"Volume atual: {self.current_volume}%.")
        self._announce(" ".join(status_parts))
