import os

import wx

from .constants import PLAYLIST_WILDCARD, SUPPORTED_MEDIA_EXTENSIONS
from .equalizer_panel import EqualizerTabPanel
from .playlists import ScreenTabState
from .playlist_io import playlist_display_name, save_playlist
from .preferences_dialog import PreferencesDialog


class FrameCommandMixin:
    def on_open(self, _event):
        wildcard = (
            "Mídia suportada|"
            + ";".join(f"*{ext}" for ext in sorted(SUPPORTED_MEDIA_EXTENSIONS))
            + "|Todos os arquivos|*.*"
        )
        with wx.FileDialog(
            self,
            "Escolha um ou mais arquivos de mídia",
            defaultDir=self._default_dialog_directory(),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            paths = dialog.GetPaths()

        if not paths:
            return

        self._open_media_paths(paths)

    def on_open_folder(self, _event):
        with wx.DirDialog(
            self,
            "Escolha uma pasta para navegar",
            defaultPath=self._default_dialog_directory(),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            folder_path = dialog.GetPath()

        self._open_folder_path(folder_path)

    def on_open_playlist(self, _event):
        with wx.FileDialog(
            self,
            "Abrir playlist",
            defaultDir=self._default_dialog_directory(),
            wildcard=PLAYLIST_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            playlist_path = dialog.GetPath()

        self._open_playlist_path(playlist_path)

    def on_save_playlist(self, _event):
        state = self._get_playlist_state()
        if not state or not state.items:
            self._announce("A playlist atual está vazia.")
            return

        default_name = os.path.basename(state.source_path) if state.source_path else f"{state.title}.m3u8"
        default_dir = os.path.dirname(state.source_path) if state.source_path else self._default_dialog_directory()

        with wx.FileDialog(
            self,
            "Salvar playlist",
            wildcard=PLAYLIST_WILDCARD,
            defaultDir=default_dir,
            defaultFile=default_name,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            playlist_path = dialog.GetPath()

        if not os.path.splitext(playlist_path)[1]:
            playlist_path += ".m3u8"

        save_playlist(playlist_path, state.items)
        self._remember_directory(playlist_path)
        state.source_path = playlist_path
        state.title = playlist_display_name(playlist_path)
        active_index = self._get_active_playlist_index()
        if active_index != wx.NOT_FOUND:
            self.notebook.SetPageText(active_index, state.title)
        self._update_title()
        self._refresh_playlist_browser()
        self._add_recent_path("recent_playlists", playlist_path)
        self._announce(f"Playlist salva: {state.title}.")

    def on_recent_menu_action(self, event):
        action = self._recent_menu_actions.get(event.GetId())
        if not action:
            event.Skip()
            return

        action_kind, attribute_name, path = action
        if action_kind == "clear":
            announcements = {
                "recent_media_files": "Arquivos recentes limpos.",
                "recent_folders": "Pastas recentes limpas.",
                "recent_playlists": "Playlists recentes limpas.",
            }
            self._clear_recent_paths(attribute_name, announcements.get(attribute_name, "Itens recentes limpos."))
            return

        if path and attribute_name == "recent_media_files":
            if self._open_media_paths([path]):
                return
        elif path and attribute_name == "recent_folders":
            if self._open_folder_path(path):
                return
        elif path and attribute_name == "recent_playlists":
            if self._open_playlist_path(path):
                return

        if path:
            self._remove_recent_path(attribute_name, path)
        self._announce("O item recente selecionado não está mais disponível.")

    def on_new_playlist(self, _event):
        tab_index = self._create_empty_playlist_tab(select=False)
        self._select_tab(tab_index, announce=True)

    def on_previous_track(self, _event):
        self._play_adjacent_item(-1)

    def on_play_pause(self, _event):
        self._toggle_play_pause()

    def on_stop(self, _event):
        state = self._get_playlist_state()
        self.player.stop()
        if state:
            state.was_playing = False
            state.last_position_ms = 0
        self._update_time_bar()
        self._announce("Parado.")

    def on_next_track(self, _event):
        self._play_adjacent_item(1)

    def on_toggle_shuffle(self, _event):
        self._toggle_shuffle()

    def on_cycle_repeat_mode(self, _event):
        self._cycle_repeat_mode()

    def on_announce_time(self, _event):
        self._announce_playback_time()

    def on_announce_volume(self, _event):
        self._announce_current_volume()

    def on_announce_status(self, _event):
        self._announce_player_status()

    def on_close_current_media(self, _event):
        self._close_current_media()

    def on_toggle_playlist_browser(self, _event=None):
        self._toggle_navigation_mode()

    def on_playlist_browser_activate_item(self, item_index):
        state = self._get_playlist_state()
        if not state:
            return

        if state.is_folder_tab:
            entries = self._get_folder_entries(state)
            if not 0 <= item_index < len(entries):
                return

            target_entry = entries[item_index]
            previous_path = state.folder_current_path
            state.folder_selected_path = target_entry.path
            if target_entry.is_directory:
                selected_path = previous_path if target_entry.is_parent else None
                self._enter_folder_directory(target_entry.path, selected_path=selected_path, announce=True)
            else:
                self._preview_folder_file(target_entry.path, announce=True)
            return

        if not 0 <= item_index < len(state.items):
            return

        state.select_index(item_index)
        self._play_media(index=self._get_active_playlist_index())

    def on_playlist_browser_remove_item(self, item_index):
        self._remove_item_from_current_playlist(item_index)

    def on_playlist_browser_preview_item(self, item_index):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab:
            return

        entries = self._get_folder_entries(state)
        if not 0 <= item_index < len(entries):
            return

        target_entry = entries[item_index]
        state.folder_selected_path = target_entry.path
        if target_entry.is_file:
            self._preview_folder_file(target_entry.path, announce=False)
            return

        self._refresh_playlist_browser()

    def on_playlist_browser_go_back(self):
        self._go_back_folder()

    def on_next_tab(self, _event):
        self._cycle_tabs(1)

    def on_previous_tab(self, _event):
        self._cycle_tabs(-1)

    def on_open_preferences(self, _event):
        previous_settings = self.settings
        dialog = PreferencesDialog(self, self.settings)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self.settings = dialog.get_settings()
        finally:
            dialog.Destroy()

        if not self.settings.remember_last_folder:
            self.settings.last_open_dir = ""

        self._save_settings()

        if self.current_volume == previous_settings.default_volume:
            self.current_volume = self.settings.default_volume
            self.player.audio_set_volume(self.current_volume)

        self._announce("Preferências salvas.")

    def on_tab_changed(self, event):
        if self._suppress_tab_change_event:
            event.Skip()
            return

        old_index = event.GetOldSelection()
        if old_index != wx.NOT_FOUND and self._get_playlist_state(old_index):
            self._capture_tab_state(old_index)

        new_index = event.GetSelection()
        if new_index != wx.NOT_FOUND:
            self._activate_tab(new_index, announce=True)

        event.Skip()

    def on_progress_timer(self, _event):
        self._update_time_bar()

    def on_video_panel_resize(self, _event):
        self._bind_player_to_window()

    def on_video_panel_focus(self, _event):
        wx.CallAfter(self.SetFocus)

    def _equalizer_page_is_active(self):
        if not hasattr(self, "notebook"):
            return False

        current_page = self.notebook.GetCurrentPage()
        return isinstance(current_page, EqualizerTabPanel)

    def _window_is_descendant_of(self, window, ancestor):
        current_window = window
        while isinstance(current_window, wx.Window):
            if current_window == ancestor:
                return True
            current_window = current_window.GetParent()

        return False

    def _equalizer_page_has_focus(self, event):
        if not self._equalizer_page_is_active():
            return False

        equalizer_panel = self.notebook.GetCurrentPage()
        focused_window = wx.Window.FindFocus()
        if self._window_is_descendant_of(focused_window, equalizer_panel):
            return True

        event_window = event.GetEventObject()
        if isinstance(event_window, wx.Window) and self._window_is_descendant_of(event_window, equalizer_panel):
            return True

        return False

    def _should_defer_key_to_equalizer_controls(self, event):
        if not self._equalizer_page_is_active():
            return False

        if event.ControlDown():
            return False

        if event.GetKeyCode() == wx.WXK_F6:
            return False

        return self._equalizer_page_has_focus(event) or self._equalizer_page_is_active()

    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        browser = self._get_browser_panel()
        current_tab = self._get_tab_state()

        if key_code == wx.WXK_F6:
            self._toggle_navigation_mode()
            return

        if key_code == wx.WXK_ESCAPE and isinstance(current_tab, ScreenTabState):
            self._close_current_tab()
            return

        if event.ControlDown() and key_code == wx.WXK_TAB:
            self._cycle_tabs(-1 if event.ShiftDown() else 1)
            return

        if self._should_defer_key_to_equalizer_controls(event):
            event.Skip()
            return

        if browser and browser.is_item_navigation_active() and not event.ControlDown() and not event.AltDown():
            event.Skip()
            return

        if not event.ControlDown() and not event.AltDown() and key_code in (ord("E"), ord("e")):
            self._toggle_shuffle()
            return

        if not event.ControlDown() and not event.AltDown() and key_code in (ord("R"), ord("r")):
            self._cycle_repeat_mode()
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_UP:
            self._move_current_item(-1)
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_DOWN:
            self._move_current_item(1)
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_LEFT:
            self._play_adjacent_item(-1)
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_RIGHT:
            self._play_adjacent_item(1)
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_HOME:
            self._jump_to_playlist_boundary(to_last=False)
            return

        if event.AltDown() and not event.ControlDown() and key_code == wx.WXK_END:
            self._jump_to_playlist_boundary(to_last=True)
            return

        if event.ControlDown() and key_code == wx.WXK_PAGEUP:
            self._play_adjacent_item(-1)
            return

        if event.ControlDown() and key_code == wx.WXK_PAGEDOWN:
            self._play_adjacent_item(1)
            return

        if event.ControlDown() and key_code in (ord("T"), ord("t")):
            self.on_new_playlist(None)
            return

        if event.ControlDown() and event.ShiftDown() and key_code in (ord("P"), ord("p")):
            self.on_open_playlist(None)
            return

        if event.ControlDown() and event.ShiftDown() and key_code in (ord("E"), ord("e")):
            self.on_open_equalizer(None)
            return

        if event.ControlDown() and event.ShiftDown() and key_code in (ord("S"), ord("s")):
            self.on_save_playlist(None)
            return

        if event.ControlDown() and key_code in (ord("L"), ord("l")):
            self.on_toggle_playlist_browser(None)
            return

        if event.ControlDown() and key_code == ord(","):
            self.on_open_preferences(None)
            return

        if event.ControlDown() and key_code in (ord("W"), ord("w")):
            self._close_current_media()
            return

        if not event.ControlDown() and not event.AltDown() and key_code in (ord("T"), ord("t")):
            self._announce_playback_time()
            return

        if not event.ControlDown() and not event.AltDown() and key_code in (ord("V"), ord("v")):
            self._announce_current_volume()
            return

        if not event.ControlDown() and not event.AltDown() and key_code in (ord("S"), ord("s")):
            self._announce_player_status()
            return

        if key_code == wx.WXK_TAB:
            self.SetFocus()
            return

        if key_code == wx.WXK_SPACE:
            self._toggle_play_pause()
            return

        if key_code == wx.WXK_HOME:
            self._seek_to_start()
            return

        if key_code == wx.WXK_END:
            self._seek_to_end()
            return

        if key_code == wx.WXK_LEFT:
            self._seek_relative(-self.settings.seek_step_ms)
            return

        if key_code == wx.WXK_RIGHT:
            self._seek_relative(self.settings.seek_step_ms)
            return

        if key_code == wx.WXK_UP:
            self._change_volume(self.settings.volume_step)
            return

        if key_code == wx.WXK_DOWN:
            self._change_volume(-self.settings.volume_step)
            return

        event.Skip()

    def on_exit(self, _event):
        self.Close()

    def on_close(self, event):
        if not getattr(self, "_update_restart_pending", False) and self.settings.confirm_on_exit and event.CanVeto():
            with wx.MessageDialog(
                self,
                "Deseja realmente sair do KeyTune?",
                "Confirmar saída",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            ) as dialog:
                if dialog.ShowModal() != wx.ID_YES:
                    event.Veto()
                    return

        if hasattr(self, "progress_timer") and self.progress_timer.IsRunning():
            self.progress_timer.Stop()
        self._dispose_equalizer_ui_cache()
        self._save_session()
        self._shutdown_player_backend()
        self.player.stop()
        self.announcer.close()
        self.Destroy()
