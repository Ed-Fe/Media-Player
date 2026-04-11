import os

import wx

from .constants import (
    APP_TITLE,
    PLAYBACK_RESTART_THRESHOLD_MS,
    REPEAT_ALL,
    REPEAT_MODE_LABELS,
    REPEAT_MODES,
    REPEAT_OFF,
    REPEAT_ONE,
    RESTORE_DELAY_MS,
)
from .media import discover_folder_entries, discover_media_files, folder_display_name
from .playlist_io import load_playlist, playlist_display_name
from .playlists import (
    PlaylistState,
    ScreenTabState,
    build_folder_tab_title,
    build_playlist_title,
    default_playlist_title,
)


class FrameLibraryMixin:
    def _insert_tab(self, state, page, select=False, index=None):
        if index is None:
            index = len(self.playlists)

        index = max(0, min(index, len(self.playlists)))
        self.playlists.insert(index, state)

        if index >= self.notebook.GetPageCount():
            self.notebook.AddPage(page, state.title, select=select)
        else:
            self.notebook.InsertPage(index, page, state.title, select=select)

        if isinstance(state, PlaylistState) and self.active_playlist_index is None:
            self.active_playlist_index = index

        return index

    def _get_tab_state(self, index=None):
        if not self.playlists:
            return None

        if index is None:
            index = self.notebook.GetSelection()

        if index == wx.NOT_FOUND or not 0 <= index < len(self.playlists):
            return None

        return self.playlists[index]

    def _get_active_playlist_index(self):
        if (
            self.active_playlist_index is not None
            and 0 <= self.active_playlist_index < len(self.playlists)
            and isinstance(self.playlists[self.active_playlist_index], PlaylistState)
        ):
            return self.active_playlist_index

        for index, state in enumerate(self.playlists):
            if isinstance(state, PlaylistState):
                self.active_playlist_index = index
                return index

        self.active_playlist_index = None
        return wx.NOT_FOUND

    def _get_active_playlist_state(self):
        active_index = self._get_active_playlist_index()
        if active_index == wx.NOT_FOUND:
            return None

        return self.playlists[active_index]

    def _open_screen_tab(
        self,
        screen_id,
        title,
        page_factory,
        *,
        select=True,
        activation_message=None,
        on_activate=None,
        on_close=None,
    ):
        for index, state in enumerate(self.playlists):
            if isinstance(state, ScreenTabState) and state.screen_id == screen_id:
                state.title = title
                state.activation_message = activation_message
                state.on_activate = on_activate
                state.on_close = on_close
                self.notebook.SetPageText(index, title)
                if select:
                    self._select_tab(index, announce=True)
                return index

        page = page_factory(self.notebook)
        state = ScreenTabState(
            title=title,
            screen_id=screen_id,
            activation_message=activation_message,
            on_activate=on_activate,
            on_close=on_close,
        )
        tab_index = self._insert_tab(state, page, select=select)
        if select:
            self._activate_tab(tab_index, announce=False)
        return tab_index

    def _create_empty_playlist_tab(self, select=False):
        tab_number = len(self.playlists) + 1
        title = default_playlist_title(tab_number)
        page = self._create_playlist_page()
        state = PlaylistState(
            title=title,
            shuffle_enabled=self.settings.shuffle_new_playlists,
            repeat_mode=self.settings.repeat_mode_new_playlists,
        )
        return self._insert_tab(state, page, select=select)

    def _reset_playlist_tabs(self):
        while self.notebook.GetPageCount():
            self.notebook.DeletePage(0)

        self.playlists = []
        self.active_playlist_index = None
        self._create_empty_playlist_tab(select=True)

    def _select_tab(self, index, announce=True):
        current_index = self.notebook.GetSelection()
        if index == current_index:
            if announce:
                self._activate_tab(index, announce=True)
            return

        if current_index != wx.NOT_FOUND and isinstance(self._get_tab_state(current_index), PlaylistState):
            self._capture_tab_state(current_index)

        self.notebook.ChangeSelection(index)
        self._activate_tab(index, announce=announce)

    def _get_playlist_state(self, index=None):
        if index is None:
            selected_state = self._get_tab_state()
            if isinstance(selected_state, PlaylistState):
                return selected_state

            return self._get_active_playlist_state()

        state = self._get_tab_state(index)
        return state if isinstance(state, PlaylistState) else None

    def _get_current_tab_index(self):
        index = self.notebook.GetSelection()
        return 0 if index == wx.NOT_FOUND else index

    def _get_video_panel(self, index=None):
        if index is None:
            selected_state = self._get_tab_state()
            if isinstance(selected_state, PlaylistState):
                index = self.notebook.GetSelection()
            else:
                index = self._get_active_playlist_index()

        if index == wx.NOT_FOUND or index is None:
            return None

        if not 0 <= index < self.notebook.GetPageCount():
            return None

        page = self.notebook.GetPage(index)
        if not page:
            return None

        return getattr(page, "video_panel", None)

    def _get_browser_panel(self, index=None):
        if index is None:
            index = self.notebook.GetSelection()

        if index == wx.NOT_FOUND or index is None:
            return None

        if not 0 <= index < self.notebook.GetPageCount():
            return None

        page = self.notebook.GetPage(index)
        if not page:
            return None

        return getattr(page, "browser_panel", None)

    def _prepare_playlist_tab(self, items, title, source_path=None):
        current_index = self.notebook.GetSelection()
        current_tab = self._get_tab_state(current_index)
        state = current_tab if isinstance(current_tab, PlaylistState) else self._get_active_playlist_state()

        if isinstance(current_tab, PlaylistState) and current_tab.is_empty:
            target_index = current_index
            state = current_tab
        elif state and state.is_empty:
            target_index = self._get_active_playlist_index()
        else:
            target_index = self._create_empty_playlist_tab(select=False)
            state = self._get_playlist_state(target_index)

        state.title = title
        state.set_items(items, start_index=0)
        state.source_path = source_path
        self.notebook.SetPageText(target_index, title)
        self._select_tab(target_index, announce=False)
        self._refresh_playlist_browser()
        return target_index

    def _activate_tab(self, index, announce=True):
        tab_state = self._get_tab_state(index)
        if not tab_state:
            return

        if isinstance(tab_state, ScreenTabState):
            self._update_title()
            if callable(tab_state.on_activate):
                tab_state.on_activate()
            if announce:
                self._announce(tab_state.activation_message or f"Aba {index + 1}: {tab_state.title}.")
            return

        state = self._get_playlist_state(index)
        if not state:
            return

        self.active_playlist_index = index
        self._apply_equalizer_state(state)

        if not state.current_media_path:
            self._unload_player()
            self._update_title()
            self._refresh_playlist_browser()
            if announce:
                if state.is_folder_tab and state.folder_current_path:
                    self._announce(
                        f"Aba {index + 1}: {state.title}. Pasta atual: {folder_display_name(state.folder_current_path)}."
                    )
                else:
                    self._announce(f"{state.title}. Nenhuma mídia tocando agora.")
            return

        pause_after_restore = not state.was_playing
        self._update_title()
        self._refresh_playlist_browser()
        announce_message = (
            f"Aba {index + 1}: {state.title}. {self._describe_playlist_position(state)}"
            if announce
            else None
        )
        self._queue_media_start(
            state.current_media_path,
            tab_index=index,
            announce_message=announce_message,
            restore_position_ms=state.last_position_ms,
            pause_after_start=pause_after_restore,
        )

    def _repeat_mode_message(self, repeat_mode):
        return REPEAT_MODE_LABELS.get(repeat_mode, REPEAT_MODE_LABELS[REPEAT_OFF])

    def _describe_playlist_position(self, state):
        if not state.current_media_path:
            if state.is_folder_tab and state.folder_current_path:
                return f"Pasta atual: {folder_display_name(state.folder_current_path)}."
            return "Nenhuma mídia tocando agora."

        media_name = self._media_label(state.current_media_path)
        if state.is_folder_tab:
            return f"Pasta atual: {folder_display_name(state.folder_current_path)}."

        if state.item_count <= 1 or not 0 <= state.current_index < state.item_count:
            return f"Item atual: {media_name}."

        return f"Item atual: {media_name}. Item {state.current_index + 1} de {state.item_count}."

    def _play_media(self, media_path=None, index=None, announce_message=None):
        state = self._get_playlist_state(index)
        if not state:
            return

        if media_path is not None and state.current_media_path != media_path:
            if media_path in state.items:
                state.select_index(state.items.index(media_path))
            else:
                state.current_media_path = media_path

        if not state.current_media_path:
            return

        state.was_playing = True
        state.last_position_ms = 0
        self._update_title()
        self._update_time_bar()
        self._refresh_playlist_browser()
        target_index = self._get_active_playlist_index() if index is None else index
        self._queue_media_start(
            state.current_media_path,
            tab_index=target_index,
            announce_message=announce_message,
        )

    def _update_title(self):
        current_tab = self._get_tab_state()
        if isinstance(current_tab, ScreenTabState):
            title_parts = [APP_TITLE, current_tab.title]
            active_state = self._get_active_playlist_state()
            if active_state and active_state.current_media_path:
                title_parts.append(self._media_label(active_state.current_media_path))
            self.SetTitle(" — ".join(title_parts))
            return

        state = self._get_playlist_state()
        if not state:
            self.SetTitle(APP_TITLE)
            return

        if not state.current_media_path:
            if state.is_folder_tab and state.folder_current_path:
                self.SetTitle(f"{APP_TITLE} — {state.title}")
                return

            self.SetTitle(APP_TITLE)
            return

        media_name = self._media_label(state.current_media_path)
        self.SetTitle(f"{APP_TITLE} — {state.title} — {media_name}")

    def _play_adjacent_item(self, direction):
        state = self._get_playlist_state()
        if not state or not state.items:
            self._announce("Nenhuma playlist carregada.")
            return

        if direction < 0 and self.player.get_media() is not None:
            current_time = self.player.get_time()
            if current_time is not None and current_time > PLAYBACK_RESTART_THRESHOLD_MS:
                self.player.set_time(0)
                self._update_time_bar()
                self._announce("Início do item atual.")
                return

        should_wrap = state.repeat_mode == REPEAT_ALL
        target = state.move_in_playback_order(-1 if direction < 0 else 1, wrap=should_wrap)
        if not target:
            boundary_message = "Você já está no primeiro item." if direction < 0 else "Você já está no último item."
            self._announce(boundary_message)
            return

        self._play_media(index=self._get_active_playlist_index())

    def _jump_to_playlist_boundary(self, to_last=False):
        state = self._get_playlist_state()
        if not state or not state.items:
            self._announce("Nenhuma playlist carregada.")
            return

        target_index = len(state.items) - 1 if to_last else 0
        if state.current_index == target_index:
            boundary_message = "Você já está no último item." if to_last else "Você já está no primeiro item."
            self._announce(boundary_message)
            return

        state.select_index(target_index)
        self._play_media(index=self._get_active_playlist_index())

    def _move_current_item(self, direction):
        state = self._get_playlist_state()
        if not state or not state.items:
            self._announce("Nenhuma playlist carregada.")
            return

        if state.is_folder_tab:
            self._announce("Não é possível reordenar arquivos no navegador de pastas.")
            return

        if len(state.items) < 2:
            self._announce("A playlist precisa de pelo menos dois itens para reordenar.")
            return

        current_index = state.current_index
        if current_index < 0 or current_index >= len(state.items):
            if state.current_media_path in state.items:
                current_index = state.items.index(state.current_media_path)
                state.current_index = current_index
            else:
                self._announce("Nenhum item atual para reordenar.")
                return

        target_index = current_index + direction
        if not 0 <= target_index < len(state.items):
            boundary_message = "O item já está no topo da playlist." if direction < 0 else "O item já está no final da playlist."
            self._announce(boundary_message)
            return

        moved_item = state.items.pop(current_index)
        state.items.insert(target_index, moved_item)
        state.refresh_browser_item_labels()
        state.current_index = target_index
        state.current_media_path = moved_item
        state.reset_playback_order(preferred_index=target_index)
        self._refresh_playlist_browser()
        self._announce(
            f"Item movido para a posição {target_index + 1} de {state.item_count}: {self._media_label(moved_item)}."
        )

    def _toggle_shuffle(self):
        state = self._get_playlist_state()
        if not state:
            self._announce("Nenhuma playlist ativa.")
            return

        state.shuffle_enabled = not state.shuffle_enabled
        preferred_index = state.current_index if state.current_index >= 0 else 0
        state.reset_playback_order(preferred_index=preferred_index)
        status = "ativado" if state.shuffle_enabled else "desativado"
        self._announce(f"Modo aleatório {status}.")
        self._refresh_playlist_browser()

    def _cycle_repeat_mode(self):
        state = self._get_playlist_state()
        if not state:
            self._announce("Nenhuma playlist ativa.")
            return

        current_mode_index = REPEAT_MODES.index(state.repeat_mode)
        state.repeat_mode = REPEAT_MODES[(current_mode_index + 1) % len(REPEAT_MODES)]
        self._announce(self._repeat_mode_message(state.repeat_mode) + ".")
        self._refresh_playlist_browser()

    def _remove_item_from_current_playlist(self, item_index, announce_prefix="Item removido"):
        state = self._get_playlist_state()
        if state and state.is_folder_tab:
            self._announce("Use Ctrl+W para fechar a prévia atual ou Backspace para voltar de pasta.")
            return

        if not state or not 0 <= item_index < len(state.items):
            self._announce("Nenhum item válido selecionado.")
            return

        removed_path = state.items[item_index]
        removed_name = self._media_label(removed_path)
        removed_current_item = item_index == state.current_index

        if removed_current_item:
            self.player.stop()

        state.items.pop(item_index)
        state.refresh_browser_item_labels()

        if not state.items:
            state.clear()
            self._unload_player()
            self._update_title()
            self._refresh_playlist_browser()
            self._announce(f"{announce_prefix}: {removed_name}. Playlist vazia.")
            return

        if removed_current_item:
            next_index = min(item_index, len(state.items) - 1)
            state.select_index(next_index)
            self._play_media(
                index=self._get_active_playlist_index(),
                announce_message=f"{announce_prefix}: {removed_name}. {self._describe_playlist_position(state)}",
            )
            return

        if item_index < state.current_index:
            state.current_index -= 1

        state.current_media_path = state.items[state.current_index]
        state.reset_playback_order(preferred_index=state.current_index)
        self._refresh_playlist_browser()
        self._announce(f"{announce_prefix}: {removed_name}. {state.item_count} itens na playlist.")

    def _close_current_media(self):
        current_tab = self._get_tab_state()
        if isinstance(current_tab, ScreenTabState):
            self._close_current_tab()
            return

        state = self._get_playlist_state()
        if state and state.is_folder_tab and state.current_media_path:
            state.current_index = -1
            state.current_media_path = None
            state.last_position_ms = 0
            state.was_playing = False
            self._unload_player()
            self._update_title()
            self._refresh_playlist_browser()
            self._announce("Prévia fechada.")
            return

        if not state or not state.current_media_path:
            self._close_current_tab()
            return

        self._remove_item_from_current_playlist(state.current_index, announce_prefix="Mídia fechada")

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

    def _get_folder_entries(self, state=None):
        state = state or self._get_playlist_state()
        if not state or not state.is_folder_tab or not state.folder_current_path:
            return []

        if state.folder_entries:
            return list(state.folder_entries)

        try:
            entries = discover_folder_entries(state.folder_current_path)
        except OSError:
            entries = []

        state.set_folder_entries(entries)
        return list(entries)

    def _configure_folder_tab_state(self, state, folder_path, root_path=None, selected_path=None):
        normalized_folder_path = self._normalize_path(folder_path)
        if not normalized_folder_path or not os.path.isdir(normalized_folder_path):
            return False

        normalized_root_path = self._normalize_path(root_path) if root_path else normalized_folder_path
        if not normalized_root_path:
            normalized_root_path = normalized_folder_path

        state.set_folder_location(
            root_path=normalized_root_path,
            current_path=normalized_folder_path,
            selected_path=selected_path,
        )
        state.title = build_folder_tab_title(normalized_folder_path)
        state.source_path = None

        try:
            folder_entries = discover_folder_entries(normalized_folder_path)
        except OSError:
            folder_entries = []

        try:
            media_files = discover_media_files(normalized_folder_path)
        except OSError:
            media_files = []

        state.set_folder_entries(folder_entries)
        state.set_items(media_files, auto_select=False)
        return True

    def _prepare_folder_tab(self, folder_path):
        current_index = self.notebook.GetSelection()
        current_tab = self._get_tab_state(current_index)
        state = current_tab if isinstance(current_tab, PlaylistState) else self._get_active_playlist_state()

        if isinstance(current_tab, PlaylistState) and current_tab.is_empty:
            target_index = current_index
            state = current_tab
        elif state and state.is_empty:
            target_index = self._get_active_playlist_index()
        else:
            target_index = self._create_empty_playlist_tab(select=False)
            state = self._get_playlist_state(target_index)

        if not state or not self._configure_folder_tab_state(state, folder_path):
            return None

        self.notebook.SetPageText(target_index, state.title)
        self._select_tab(target_index, announce=False)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()
        return target_index

    def _enter_folder_directory(self, folder_path, selected_path=None, announce=True):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab:
            return False

        if not self._configure_folder_tab_state(
            state,
            folder_path,
            root_path=state.folder_root_path or folder_path,
            selected_path=selected_path,
        ):
            return False

        self.notebook.SetPageText(self._get_current_tab_index(), state.title)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()

        if announce:
            self._announce(f"Pasta atual: {folder_display_name(state.folder_current_path)}.")

        return True

    def _preview_folder_file(self, media_path, announce=True):
        state = self._get_playlist_state()
        if not state or not state.is_folder_tab or not state.folder_current_path:
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

        if normalized_media_path not in state.items:
            try:
                media_files = discover_media_files(state.folder_current_path)
            except OSError:
                media_files = []
            state.set_items(media_files, auto_select=False)

        if normalized_media_path not in state.items:
            self._announce("O arquivo selecionado não pertence à pasta atual.")
            self._refresh_playlist_browser()
            return

        if same_media_already_playing:
            state.select_index(state.items.index(normalized_media_path))
            self._refresh_playlist_browser()
            return

        state.select_index(state.items.index(normalized_media_path))
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

        self._add_recent_path("recent_folders", normalized_folder_path)

        self._focus_item_navigation(announce=False)
        self._announce(f"Pasta aberta no navegador: {folder_display_name(normalized_folder_path)}.")
        return True

    def _open_playlist_path(self, playlist_path):
        normalized_playlist_path = self._normalize_path(playlist_path)
        if not normalized_playlist_path or not os.path.isfile(normalized_playlist_path):
            return False

        self._remember_directory(normalized_playlist_path)

        items = load_playlist(normalized_playlist_path)
        if not items:
            wx.MessageBox(
                "Nenhum item válido foi encontrado na playlist selecionada.",
                "Abrir playlist",
                wx.OK | wx.ICON_INFORMATION,
            )
            return False

        title = playlist_display_name(normalized_playlist_path)
        tab_index = self._prepare_playlist_tab(items, title, source_path=normalized_playlist_path)
        self._play_media(
            index=tab_index,
            announce_message=f"Playlist carregada: {title}. {len(items)} item(ns).",
        )
        self._add_recent_path("recent_playlists", normalized_playlist_path)
        return True

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
            )
            return

        browser.update_playlist(current_state)

    def _close_current_tab(self):
        current_index = self._get_current_tab_index()
        current_state = self._get_tab_state(current_index)
        total_tabs = self.notebook.GetPageCount()

        if total_tabs <= 1:
            self._announce("Não é possível fechar a última aba.")
            return False

        next_index = current_index if current_index < total_tabs - 1 else current_index - 1
        active_playlist_index = self._get_active_playlist_index()

        self._suppress_tab_change_event = True
        try:
            if isinstance(current_state, ScreenTabState) and callable(current_state.on_close):
                current_state.on_close()

            self.playlists.pop(current_index)
            self.notebook.DeletePage(current_index)

            if active_playlist_index != wx.NOT_FOUND:
                if current_index == active_playlist_index:
                    self.active_playlist_index = None
                elif current_index < active_playlist_index:
                    self.active_playlist_index = active_playlist_index - 1

            self.notebook.ChangeSelection(next_index)
        finally:
            self._suppress_tab_change_event = False

        self._activate_tab(next_index, announce=False)
        self._refresh_playlist_browser()

        next_state = self._get_tab_state(next_index)
        if next_state:
            self._announce(
                f"Aba fechada: {current_state.title if current_state else 'sem nome'}. "
                + (
                    f"Agora em {next_state.title}. {self._describe_playlist_position(next_state)}"
                    if isinstance(next_state, PlaylistState)
                    else f"Agora em {next_state.title}."
                )
            )
        else:
            self._announce("Aba fechada.")

        return True

    def _handle_media_end(self):
        state = self._get_playlist_state()
        if not state:
            self._announce("Mídia finalizada.")
            return

        state.was_playing = False
        state.last_position_ms = 0

        if state.is_folder_tab:
            self._update_time_bar()
            self._refresh_playlist_browser()
            return

        if state.repeat_mode == REPEAT_ONE and state.current_media_path:
            self._play_media(
                index=self._get_active_playlist_index(),
                announce_message=f"Repetindo faixa atual. {self._describe_playlist_position(state)}",
            )
            return

        should_wrap = state.repeat_mode == REPEAT_ALL
        wrapped_cycle = False
        if should_wrap:
            state.sync_playback_order()
            if state.shuffle_enabled:
                wrapped_cycle = state.playback_order_position == len(state.playback_order) - 1
            else:
                wrapped_cycle = state.current_index == state.item_count - 1

        target = state.move_in_playback_order(1, wrap=should_wrap)
        if target:
            loop_prefix = "Nova volta da playlist. " if wrapped_cycle else ""
            self._play_media(
                index=self._get_active_playlist_index(),
                announce_message=f"{loop_prefix}{self._describe_playlist_position(state)}",
            )
            return

        self._announce(f"Playlist {state.title} finalizada.")

    def _cycle_tabs(self, step):
        total_tabs = self.notebook.GetPageCount()
        if total_tabs <= 1:
            return

        current_index = self.notebook.GetSelection()
        next_index = (current_index + step) % total_tabs
        if next_index == current_index:
            return

        self._select_tab(next_index, announce=True)
