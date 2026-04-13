import os

import wx

from ..library import folder_display_name, is_playlist_source, is_remote_media_path, playlist_display_name, scan_folder_contents
from ..playlists import build_playlist_title


class FrameLibraryNavigationMixin:
    def _playlist_state_for_external_media(self):
        current_state = self._get_tab_state(self._get_current_tab_index())
        if getattr(current_state, "is_screen_tab", False):
            current_state = None

        candidates = [current_state, self._get_active_playlist_state()]
        for candidate in candidates:
            if not candidate:
                continue
            if candidate.is_folder_tab or candidate.is_loading:
                continue
            return candidate

        return None

    def _append_media_paths_to_playlist(self, paths, state):
        if not state or state.is_folder_tab or state.is_loading:
            return False

        normalized_paths = []
        for path in paths:
            normalized_path = self._normalize_path(path)
            if normalized_path and os.path.isfile(normalized_path):
                normalized_paths.append(normalized_path)

        if not normalized_paths:
            return False

        current_index = state.current_index
        current_media_path = state.current_media_path

        state.finish_library_load()
        state.clear_folder_location()
        state.items.extend(normalized_paths)
        state.browser_item_labels.extend(os.path.basename(path) or path for path in normalized_paths)
        state.refresh_browser_item_labels()

        if 0 <= current_index < len(state.items):
            state.current_index = current_index
            state.current_media_path = state.items[current_index]
        elif current_media_path and current_media_path in state.items:
            restored_index = state.items.index(current_media_path)
            state.current_index = restored_index
            state.current_media_path = state.items[restored_index]
        elif state.items:
            state.select_index(0)

        if state.current_index >= 0:
            state.reset_playback_order(preferred_index=state.current_index)

        self._remember_directory(normalized_paths[0])
        self._refresh_playlist_browser()
        self._update_title()
        self._add_recent_media_paths(normalized_paths)
        count = len(normalized_paths)
        suffix = "s" if count != 1 else ""
        self._announce(f"{count} arquivo{suffix} adicionado{suffix} à playlist {state.title}.")
        return True

    def _open_external_media_paths(self, paths):
        target_state = self._playlist_state_for_external_media()
        if target_state and not target_state.is_empty:
            target_index = self._resolve_playlist_state_index(target_state)
            appended = self._append_media_paths_to_playlist(paths, target_state)
            if appended and target_index != wx.NOT_FOUND:
                self.active_playlist_index = target_index
            return appended

        return self._open_media_paths(paths)

    def _show_loading_library_tab(self, target_index, state, announcement=None):
        self.notebook.SetPageText(target_index, state.title)
        self._select_tab(target_index, announce=False)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()
        if announcement:
            self._announce(announcement)

    def _open_media_paths(self, paths):
        normalized_paths = []
        for path in paths:
            normalized_path = self._normalize_path(path)
            if normalized_path and os.path.isfile(normalized_path):
                normalized_paths.append(normalized_path)

        if not normalized_paths:
            return False

        self._remember_directory(normalized_paths[0])

        title = build_playlist_title(normalized_paths)
        tab_index = self._prepare_playlist_tab(normalized_paths, title)
        self._play_media(index=tab_index)
        self._add_recent_media_paths(normalized_paths)
        return True

    def _prepare_folder_tab(self, folder_path):
        normalized_folder_path = self._normalize_path(folder_path)
        if not normalized_folder_path or not os.path.isdir(normalized_folder_path):
            return None

        state, target_index = self._prepare_library_target_tab()
        if not state:
            return None

        self._begin_folder_load(state, normalized_folder_path, root_path=normalized_folder_path)
        self._queue_library_request(
            {
                "kind": "folder",
                "state": state,
                "folder_path": normalized_folder_path,
                "recent_path": normalized_folder_path,
                "focus_items": True,
                "completion_announcement": f"Pasta aberta no navegador: {folder_display_name(normalized_folder_path)}.",
            }
        )
        self._show_loading_library_tab(target_index, state)
        return target_index

    def _enter_folder_directory(self, folder_path, selected_path=None, announce=True):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab:
            return False

        normalized_folder_path = self._normalize_path(folder_path)
        if not normalized_folder_path or not os.path.isdir(normalized_folder_path):
            return False

        self._begin_folder_load(
            state,
            normalized_folder_path,
            root_path=state.folder_root_path or normalized_folder_path,
            selected_path=selected_path,
        )
        self._queue_library_request(
            {
                "kind": "folder",
                "state": state,
                "folder_path": normalized_folder_path,
                "focus_items": True,
                "completion_announcement": (
                    f"Pasta atual: {folder_display_name(normalized_folder_path)}."
                    if announce
                    else None
                ),
            }
        )
        self._show_loading_library_tab(
            self._get_current_tab_index(),
            state,
            announcement=(f"Carregando pasta: {folder_display_name(normalized_folder_path)}." if announce else None),
        )

        return True

    def _preview_folder_file(self, media_path, announce=True):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab or not state.folder_current_path:
            return

        if state.is_loading:
            self._announce("A pasta ainda está sendo carregada.")
            return

        normalized_media_path = self._normalize_path(media_path)
        if not normalized_media_path or not os.path.isfile(normalized_media_path):
            self._announce("O arquivo selecionado não está mais disponível.")
            self._refresh_playlist_browser()
            return

        same_media_already_playing = (
            state.current_media_path == normalized_media_path
            and self.player.get_media() is not None
            and self.player.is_playing()
        )

        state.folder_selected_path = normalized_media_path

        if not state.contains_item(normalized_media_path):
            try:
                folder_entries, media_files = scan_folder_contents(state.folder_current_path)
            except OSError:
                folder_entries = []
                media_files = []
            state.set_folder_entries(folder_entries)
            state.set_items(media_files, auto_select=False)

        media_index = state.index_of_item(normalized_media_path)
        if media_index is None:
            self._announce("O arquivo selecionado não pertence à pasta atual.")
            self._refresh_playlist_browser()
            return

        if same_media_already_playing:
            state.select_index(media_index)
            self._refresh_playlist_browser()
            return

        state.select_index(media_index)
        announce_message = ""
        self._play_media(index=self._get_current_tab_index(), announce_message=announce_message)

    def _go_back_folder(self):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab or not state.folder_current_path:
            return

        parent_path = os.path.dirname(state.folder_current_path)
        if not parent_path or parent_path == state.folder_current_path:
            self._announce("Você já está na pasta raiz.")
            return

        self._enter_folder_directory(
            parent_path,
            selected_path=state.folder_current_path,
            announce=True,
        )

    def _open_folder_path(self, folder_path):
        normalized_folder_path = self._normalize_path(folder_path)
        if not normalized_folder_path or not os.path.isdir(normalized_folder_path):
            return False

        self._remember_directory(normalized_folder_path)

        tab_index = self._prepare_folder_tab(normalized_folder_path)
        if tab_index is None:
            return False
        self._announce(f"Carregando pasta: {folder_display_name(normalized_folder_path)}.")
        return True

    def _open_folder_as_playlist(self, folder_path):
        normalized_folder_path = self._normalize_path(folder_path)
        if not normalized_folder_path or not os.path.isdir(normalized_folder_path):
            return False

        self._remember_directory(normalized_folder_path)

        state, target_index = self._prepare_library_target_tab()
        if not state:
            return False

        title = folder_display_name(normalized_folder_path)
        previous_title = state.title
        previous_source_path = state.source_path
        self._begin_playlist_load(state, title)
        self._queue_library_request(
            {
                "kind": "folder_playlist",
                "state": state,
                "folder_path": normalized_folder_path,
                "title": title,
                "previous_title": previous_title,
                "previous_source_path": previous_source_path,
            }
        )
        self._show_loading_library_tab(target_index, state, announcement=f"Carregando pasta como playlist: {title}.")
        return True

    def _open_playlist_source(self, playlist_source):
        normalized_playlist_source = str(playlist_source or "").strip()
        if not normalized_playlist_source or not is_playlist_source(normalized_playlist_source):
            return False

        if not is_remote_media_path(normalized_playlist_source):
            normalized_playlist_source = self._normalize_path(normalized_playlist_source)
            if not normalized_playlist_source or not os.path.isfile(normalized_playlist_source):
                return False

            self._remember_directory(normalized_playlist_source)

        state, target_index = self._prepare_library_target_tab()
        if not state:
            return False

        title = playlist_display_name(normalized_playlist_source)
        previous_title = state.title
        previous_source_path = state.source_path
        self._begin_playlist_load(state, title)
        self._queue_library_request(
            {
                "kind": "playlist",
                "state": state,
                "playlist_source": normalized_playlist_source,
                "title": title,
                "previous_title": previous_title,
                "previous_source_path": previous_source_path,
            }
        )
        self._show_loading_library_tab(target_index, state, announcement=f"Carregando playlist: {title}.")
        return True

    def _open_playlist_path(self, playlist_path):
        return self._open_playlist_source(playlist_path)

    def _focus_item_navigation(self, announce=True):
        browser = self._get_browser_panel()
        if not browser:
            return

        self._refresh_playlist_browser()
        browser.focus_current_item()
        if announce:
            self._announce("Modo navegação de itens.")

    def _focus_player_controls(self, announce=True):
        self.SetFocus()
        if announce:
            self._announce("Modo controle do player.")

    def _toggle_navigation_mode(self):
        browser = self._get_browser_panel()
        if not browser:
            return

        if browser.is_item_navigation_active():
            self._focus_player_controls(announce=True)
            return

        self._focus_item_navigation(announce=True)

    def _refresh_playlist_browser(self):
        browser = self._get_browser_panel()
        if not browser:
            return

        current_state = self._get_playlist_state()
        if not current_state:
            return

        if current_state.is_folder_tab and current_state.folder_current_path:
            browser.update_folder(
                title=current_state.title,
                current_path=current_state.folder_current_path,
                entries=self._get_folder_entries(current_state),
                selected_path=current_state.folder_selected_path,
                current_media_path=current_state.current_media_path,
                entries_revision=current_state.folder_entries_revision,
                loading=current_state.is_loading,
                loading_message=current_state.loading_message,
                entry_index_map=current_state.folder_entry_index_map,
            )
            return

        browser.update_playlist(current_state)
