import queue
import os
import threading

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
from .media import discover_folder_entries, folder_display_name, scan_folder_contents
from .playlist_io import is_playlist_source, is_remote_media_path, load_playlist, playlist_display_name
from .playlists import (
    PlaylistState,
    ScreenTabState,
    build_folder_tab_title,
    build_playlist_title,
    default_playlist_title,
)


class FrameLibraryMixin:
    def _create_library_loader(self):
        self._library_request_serial = 0
        self._library_queue = queue.Queue()
        self._library_stop_event = threading.Event()
        self._library_worker = threading.Thread(target=self._library_worker_loop, daemon=True)
        self._library_worker.start()

    def _shutdown_library_loader(self):
        stop_event = getattr(self, "_library_stop_event", None)
        if stop_event is not None:
            stop_event.set()

        if hasattr(self, "_library_queue"):
            self._library_queue.put({"kind": "shutdown"})

        if hasattr(self, "_library_worker") and self._library_worker.is_alive():
            self._library_worker.join(timeout=1.0)

    def _next_library_request_serial(self):
        self._library_request_serial += 1
        return self._library_request_serial

    def _resolve_playlist_state_index(self, state):
        for index, candidate in enumerate(self.playlists):
            if candidate is state:
                return index
        return wx.NOT_FOUND

    def _is_current_playlist_state(self, state):
        current_index = self._get_current_tab_index()
        return self._get_tab_state(current_index) is state

    def _prepare_library_target_tab(self):
        current_index = self.notebook.GetSelection()
        current_tab = self._get_tab_state(current_index)
        state = current_tab if isinstance(current_tab, PlaylistState) else self._get_active_playlist_state()

        if isinstance(current_tab, PlaylistState) and current_tab.is_empty:
            return current_tab, current_index

        if state and state.is_empty:
            return state, self._get_active_playlist_index()

        target_index = self._create_empty_playlist_tab(select=False)
        return self._get_playlist_state(target_index), target_index

    def _queue_library_request(self, request):
        state = request.get("state")
        if not isinstance(state, PlaylistState):
            return None

        request_serial = self._next_library_request_serial()
        request["serial"] = request_serial
        state.library_request_serial = request_serial
        self._library_queue.put(request)
        return request_serial

    def _store_latest_library_request(self, pending_requests, request):
        state = request.get("state")
        request_key = id(state) if state is not None else (request.get("kind"), request.get("serial"))
        pending_requests[request_key] = request

    def _library_worker_loop(self):
        while True:
            request = self._library_queue.get()
            if request.get("kind") == "shutdown" or self._library_stop_event.is_set():
                return

            pending_requests = {}
            self._store_latest_library_request(pending_requests, request)
            while True:
                try:
                    newer_request = self._library_queue.get_nowait()
                except queue.Empty:
                    break

                if newer_request.get("kind") == "shutdown" or self._library_stop_event.is_set():
                    return

                self._store_latest_library_request(pending_requests, newer_request)

            for current_request in pending_requests.values():
                if self._library_stop_event.is_set():
                    return
                self._process_library_request(current_request)

    def _process_library_request(self, request):
        kind = request.get("kind")

        if kind == "folder":
            try:
                folder_entries, media_files = scan_folder_contents(request["folder_path"])
                media_item_index_map = {path: index for index, path in enumerate(media_files)}
                media_browser_labels = [os.path.basename(path) or path for path in media_files]
                folder_entry_index_map = {
                    os.path.normcase(os.path.normpath(getattr(entry, "path", ""))): index
                    for index, entry in enumerate(folder_entries)
                    if getattr(entry, "path", None)
                }
                error_message = ""
            except OSError as exc:
                folder_entries = []
                media_files = []
                media_item_index_map = {}
                media_browser_labels = []
                folder_entry_index_map = {}
                error_message = str(exc)
            except Exception as exc:
                folder_entries = []
                media_files = []
                media_item_index_map = {}
                media_browser_labels = []
                folder_entry_index_map = {}
                error_message = f"Falha inesperada ao carregar a pasta: {exc}."

            if self._library_stop_event.is_set():
                return

            wx.CallAfter(
                self._finish_folder_load_request,
                request,
                folder_entries,
                folder_entry_index_map,
                media_files,
                media_item_index_map,
                media_browser_labels,
                error_message,
            )
            return

        if kind == "folder_playlist":
            try:
                _folder_entries, media_files = scan_folder_contents(request["folder_path"])
                item_index_map = {path: index for index, path in enumerate(media_files)}
                browser_item_labels = [os.path.basename(path) or path for path in media_files]
                error_message = ""
            except OSError as exc:
                media_files = []
                item_index_map = {}
                browser_item_labels = []
                error_message = str(exc)
            except Exception as exc:
                media_files = []
                item_index_map = {}
                browser_item_labels = []
                error_message = f"Falha inesperada ao carregar a pasta: {exc}."

            if self._library_stop_event.is_set():
                return

            wx.CallAfter(
                self._finish_folder_playlist_load_request,
                request,
                media_files,
                item_index_map,
                browser_item_labels,
                error_message,
            )
            return

        if kind == "playlist":
            try:
                items = load_playlist(request["playlist_source"])
                item_index_map = {path: index for index, path in enumerate(items)}
                browser_item_labels = [os.path.basename(path) or path for path in items]
                error_message = ""
            except OSError as exc:
                items = []
                item_index_map = {}
                browser_item_labels = []
                error_message = str(exc)
            except Exception as exc:
                items = []
                item_index_map = {}
                browser_item_labels = []
                error_message = f"Falha inesperada ao carregar a playlist: {exc}."

            if self._library_stop_event.is_set():
                return

            wx.CallAfter(
                self._finish_playlist_load_request,
                request,
                items,
                item_index_map,
                browser_item_labels,
                error_message,
            )

    def _is_current_library_request(self, state, request_serial):
        if not isinstance(state, PlaylistState):
            return False

        if state.library_request_serial != request_serial:
            return False

        return self._resolve_playlist_state_index(state) != wx.NOT_FOUND

    def _begin_playlist_load(self, state, playlist_path, title):
        state.finish_library_load()
        state.clear_folder_location()
        state.title = title
        state.source_path = None
        state.set_items([], auto_select=False)
        state.begin_library_load("Carregando playlist...")

    def _begin_folder_load(self, state, folder_path, root_path=None, selected_path=None):
        normalized_root_path = self._normalize_path(root_path) if root_path else folder_path
        if not normalized_root_path:
            normalized_root_path = folder_path

        state.finish_library_load()
        state.set_folder_location(
            root_path=normalized_root_path,
            current_path=folder_path,
            selected_path=selected_path,
        )
        state.title = build_folder_tab_title(folder_path)
        state.source_path = None
        state.set_items([], auto_select=False)
        state.begin_library_load("Carregando itens da pasta...")

    def _finish_playlist_load_request(self, request, items, item_index_map, browser_item_labels, error_message):
        if self._library_stop_event.is_set():
            return

        state = request.get("state")
        request_serial = request.get("serial")
        if not self._is_current_library_request(state, request_serial):
            return

        state.finish_library_load()
        tab_index = self._resolve_playlist_state_index(state)
        if tab_index == wx.NOT_FOUND:
            return

        if error_message:
            state.title = request.get("previous_title") or state.title
            state.source_path = request.get("previous_source_path")
            state.set_items([], auto_select=False)
            self.notebook.SetPageText(tab_index, state.title)
            if self._is_current_playlist_state(state):
                self._update_title()
                self._refresh_playlist_browser()
            wx.MessageBox(error_message, "Abrir playlist", wx.OK | wx.ICON_ERROR, self)
            return

        if not items:
            state.title = request.get("previous_title") or state.title
            state.source_path = request.get("previous_source_path")
            state.set_items([], auto_select=False)
            self.notebook.SetPageText(tab_index, state.title)
            if self._is_current_playlist_state(state):
                self._update_title()
                self._refresh_playlist_browser()
            wx.MessageBox(
                "Nenhum item válido foi encontrado na playlist selecionada.",
                "Abrir playlist",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        state.title = request["title"]
        state.source_path = request["playlist_source"]
        state.set_items_prepared(items, item_index_map, browser_item_labels, start_index=0)
        self.notebook.SetPageText(tab_index, state.title)
        if not is_remote_media_path(request["playlist_source"]):
            self._add_recent_path("recent_playlists", request["playlist_source"])

        if self._is_current_playlist_state(state):
            self._play_media(
                index=tab_index,
                announce_message=f"Playlist carregada: {state.title}. {len(items)} item(ns).",
            )

    def _finish_folder_playlist_load_request(self, request, items, item_index_map, browser_item_labels, error_message):
        if self._library_stop_event.is_set():
            return

        state = request.get("state")
        request_serial = request.get("serial")
        if not self._is_current_library_request(state, request_serial):
            return

        state.finish_library_load()
        tab_index = self._resolve_playlist_state_index(state)
        if tab_index == wx.NOT_FOUND:
            return

        if error_message:
            state.title = request.get("previous_title") or state.title
            state.source_path = request.get("previous_source_path")
            state.set_items([], auto_select=False)
            self.notebook.SetPageText(tab_index, state.title)
            if self._is_current_playlist_state(state):
                self._update_title()
                self._refresh_playlist_browser()
            wx.MessageBox(error_message, "Abrir pasta como playlist", wx.OK | wx.ICON_ERROR, self)
            return

        if not items:
            state.title = request.get("previous_title") or state.title
            state.source_path = request.get("previous_source_path")
            state.set_items([], auto_select=False)
            self.notebook.SetPageText(tab_index, state.title)
            if self._is_current_playlist_state(state):
                self._update_title()
                self._refresh_playlist_browser()
            wx.MessageBox(
                "Nenhuma mídia compatível foi encontrada na pasta selecionada.",
                "Abrir pasta como playlist",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        state.title = request["title"]
        state.source_path = request["folder_path"]
        state.set_items_prepared(items, item_index_map, browser_item_labels, start_index=0)
        self.notebook.SetPageText(tab_index, state.title)

        if self._is_current_playlist_state(state):
            self._play_media(
                index=tab_index,
                announce_message=f"Pasta carregada como playlist: {state.title}. {len(items)} item(ns).",
            )

    def _finish_folder_load_request(
        self,
        request,
        folder_entries,
        folder_entry_index_map,
        media_files,
        media_item_index_map,
        media_browser_labels,
        error_message,
    ):
        if self._library_stop_event.is_set():
            return

        state = request.get("state")
        request_serial = request.get("serial")
        if not self._is_current_library_request(state, request_serial):
            return

        state.finish_library_load()
        state.set_folder_entries(folder_entries, entry_index_map=folder_entry_index_map)
        state.set_items_prepared(media_files, media_item_index_map, media_browser_labels, auto_select=False)

        tab_index = self._resolve_playlist_state_index(state)
        if tab_index == wx.NOT_FOUND:
            return

        self.notebook.SetPageText(tab_index, state.title)

        if error_message:
            if self._is_current_playlist_state(state):
                self._update_title()
                self._refresh_playlist_browser()
            self._announce(f"Não foi possível carregar a pasta selecionada: {error_message}.")
            return

        recent_path = request.get("recent_path")
        if recent_path:
            self._add_recent_path("recent_folders", recent_path)

        if self._is_current_playlist_state(state):
            self._update_title()
            self._refresh_playlist_browser()
            if request.get("focus_items"):
                browser = self._get_browser_panel(tab_index)
                if browser:
                    wx.CallAfter(browser.focus_current_item)

            completion_announcement = request.get("completion_announcement")
            if completion_announcement:
                wx.CallAfter(self._announce, completion_announcement)

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
                self._remember_screen_tab_return_context(state)
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
        self._remember_screen_tab_return_context(state)
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

    def _playlist_focus_mode(self, index=None):
        browser = self._get_browser_panel(index)
        if browser and browser.is_item_navigation_active():
            return "items"

        return "player"

    def _screen_tab_return_context(self):
        current_index = self.notebook.GetSelection() if hasattr(self, "notebook") else wx.NOT_FOUND
        current_state = self._get_tab_state(current_index)
        if isinstance(current_state, PlaylistState):
            return current_index, self._playlist_focus_mode(current_index)

        active_index = self._get_active_playlist_index()
        if active_index == wx.NOT_FOUND:
            return None, None

        return active_index, None

    def _remember_screen_tab_return_context(self, screen_state):
        if not isinstance(screen_state, ScreenTabState):
            return

        return_index, return_focus_mode = self._screen_tab_return_context()
        if isinstance(return_index, int) and return_index >= 0:
            screen_state.return_to_tab_index = return_index
        if return_focus_mode is not None:
            screen_state.return_focus_mode = return_focus_mode

    def _resolve_screen_tab_close_target(self, current_index, total_tabs, screen_state):
        fallback_index = current_index if current_index < total_tabs - 1 else current_index - 1
        preferred_index = getattr(screen_state, "return_to_tab_index", None)
        if not isinstance(preferred_index, int):
            return fallback_index

        adjusted_index = preferred_index - 1 if preferred_index > current_index else preferred_index
        if 0 <= adjusted_index < total_tabs - 1:
            return adjusted_index

        return fallback_index

    def _restore_screen_tab_focus(self, screen_state, next_state):
        if not isinstance(screen_state, ScreenTabState) or not isinstance(next_state, PlaylistState):
            return

        if screen_state.return_focus_mode == "items":
            self._focus_item_navigation(announce=False)
            return

        if screen_state.return_focus_mode == "player":
            self._focus_player_controls(announce=False)

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

    def _open_prepared_media_playlist(
        self,
        items,
        title,
        *,
        browser_item_labels=None,
        source_path=None,
        announce_message=None,
    ):
        normalized_items = list(items or [])
        if not normalized_items:
            return wx.NOT_FOUND

        if browser_item_labels is None:
            normalized_browser_labels = [os.path.basename(path) or path for path in normalized_items]
        else:
            normalized_browser_labels = list(browser_item_labels)

        if len(normalized_browser_labels) != len(normalized_items):
            normalized_browser_labels = [os.path.basename(path) or path for path in normalized_items]

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

        state.finish_library_load()
        state.clear_folder_location()
        state.title = title
        state.source_path = source_path
        state.set_items_prepared(
            normalized_items,
            {item: index for index, item in enumerate(normalized_items)},
            normalized_browser_labels,
            start_index=0,
        )

        self.notebook.SetPageText(target_index, title)
        self._select_tab(target_index, announce=False)
        self._refresh_playlist_browser()
        self._play_media(index=target_index, announce_message=announce_message)
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

        previous_active_playlist_index = self._get_active_playlist_index()
        self.active_playlist_index = index
        self._apply_equalizer_state(state)

        if state.is_loading:
            self._unload_player()
            self._update_title()
            self._refresh_playlist_browser()
            if announce:
                self._announce(state.loading_message or f"Carregando {state.title}.")
            return

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

        if previous_active_playlist_index == index and self._player_has_loaded_media(state.current_media_path):
            self._bind_player_to_window()
            self._update_title()
            self._update_time_bar()
            self._refresh_playlist_browser()
            if announce:
                self._announce(f"Aba {index + 1}: {state.title}. {self._describe_playlist_position(state)}")
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

    def _play_media(self, media_path=None, index=None, announce_message=None, allow_crossfade=False):
        state = self._get_playlist_state(index)
        if not state:
            return

        if media_path is not None and state.current_media_path != media_path:
            media_index = state.index_of_item(media_path)
            if media_index is not None:
                state.select_index(media_index)
            else:
                state.current_media_path = media_path

        if not state.current_media_path:
            return

        crossfade_state = getattr(self, "_crossfade_state", None)
        self._cancel_crossfade_transition(
            stop_incoming=True,
            stop_outgoing=bool(crossfade_state and crossfade_state.get("phase") == "running"),
            invalidate_requests=bool(crossfade_state),
        )

        state.was_playing = True
        state.last_position_ms = 0
        target_index = self._get_active_playlist_index() if index is None else index
        if allow_crossfade and self._can_crossfade_to_media(state.current_media_path):
            if self._start_crossfade(
                state.current_media_path,
                tab_index=target_index,
                announce_message=announce_message,
            ):
                return

        self._update_title()
        self._update_time_bar()
        self._refresh_playlist_browser()

        self._queue_media_start(
            state.current_media_path,
            tab_index=target_index,
            announce_message=announce_message,
        )

    def _maybe_start_automatic_crossfade(self):
        if getattr(self, "_crossfade_state", None) is not None:
            return False

        configured_crossfade_ms = self._crossfade_duration_ms()
        if configured_crossfade_ms <= 0:
            return False

        state = self._get_playlist_state()
        if not state or state.is_folder_tab or not state.current_media_path or state.repeat_mode == REPEAT_ONE:
            return False

        if self.player.get_media() is None or not self.player.is_playing():
            return False

        current_time = self.player.get_time()
        total_time = self.player.get_length()
        if current_time is None or current_time < 0 or total_time is None or total_time <= 0:
            return False

        startup_headroom_ms = self._crossfade_startup_headroom_ms()
        crossfade_window_ms = configured_crossfade_ms + startup_headroom_ms
        remaining_time = total_time - max(0, current_time)
        if remaining_time > crossfade_window_ms or remaining_time <= 0:
            return False

        should_wrap = state.repeat_mode == REPEAT_ALL
        next_media_path = state.peek_in_playback_order(1, wrap=should_wrap)
        if not next_media_path or not self._can_crossfade_to_media(next_media_path):
            return False

        wrapped_cycle = False
        if should_wrap:
            state.sync_playback_order()
            if state.shuffle_enabled:
                wrapped_cycle = state.playback_order_position == len(state.playback_order) - 1
            else:
                wrapped_cycle = state.current_index == state.item_count - 1

        target = state.move_in_playback_order(1, wrap=should_wrap)
        if not target:
            return False

        loop_prefix = "Nova volta da playlist. " if wrapped_cycle else ""
        self._play_media(
            index=self._get_active_playlist_index(),
            announce_message=f"{loop_prefix}{self._describe_playlist_position(state)}",
            allow_crossfade=True,
        )
        return True

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

        if state.is_loading:
            self.SetTitle(f"{APP_TITLE} — {state.title}")
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

        self._play_media(index=self._get_active_playlist_index(), allow_crossfade=True)

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
            media_index = state.index_of_item(state.current_media_path)
            if media_index is not None:
                current_index = media_index
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
            self._cancel_crossfade_transition(stop_incoming=True, stop_outgoing=True, invalidate_requests=True)
            self._stop_all_players(unload=False)

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

        if state.is_loading or state.folder_entries_loaded:
            return state.folder_entries

        try:
            entries = discover_folder_entries(state.folder_current_path)
        except OSError:
            entries = []

        state.set_folder_entries(entries)
        return state.folder_entries

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

        self.notebook.SetPageText(self._get_current_tab_index(), state.title)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()

        if announce:
            self._announce(f"Carregando pasta: {folder_display_name(normalized_folder_path)}.")

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
        self._begin_playlist_load(state, normalized_folder_path, title)
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

        self.notebook.SetPageText(target_index, state.title)
        self._select_tab(target_index, announce=False)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()
        self._announce(f"Carregando pasta como playlist: {title}.")
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
        self._begin_playlist_load(state, normalized_playlist_source, title)
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

        self.notebook.SetPageText(target_index, state.title)
        self._select_tab(target_index, announce=False)
        self._unload_player()
        self._update_title()
        self._refresh_playlist_browser()
        self._announce(f"Carregando playlist: {title}.")
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

    def _close_current_tab(self):
        current_index = self._get_current_tab_index()
        current_state = self._get_tab_state(current_index)
        total_tabs = self.notebook.GetPageCount()

        if total_tabs <= 1:
            self._announce("Não é possível fechar a última aba.")
            return False

        if isinstance(current_state, ScreenTabState):
            self._capture_active_playlist_state()

        next_index = (
            self._resolve_screen_tab_close_target(current_index, total_tabs, current_state)
            if isinstance(current_state, ScreenTabState)
            else (current_index if current_index < total_tabs - 1 else current_index - 1)
        )
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
        if isinstance(current_state, ScreenTabState):
            self._restore_screen_tab_focus(current_state, next_state)

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
