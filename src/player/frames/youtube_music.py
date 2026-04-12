import os
import threading

import wx

from player.youtube_music import YouTubeMusicBrowserAuthDialog, YouTubeMusicService, extract_playlist_id_from_source

from ..playlists import PlaylistState


class FrameYouTubeMusicMixin:
    _YOUTUBE_MUSIC_BACKGROUND_TASK_TIMEOUT_MS = 20000

    def _get_youtube_music_service(self):
        service = getattr(self, "_youtube_music_service", None)
        if service is None:
            service = YouTubeMusicService()
            self._youtube_music_service = service
        return service

    def _refresh_youtube_music_menu_state(self):
        if not hasattr(self, "youtube_music_menu"):
            return

        service = self._get_youtube_music_service()
        has_saved_auth = service.has_saved_browser_auth()
        operation_in_progress = bool(getattr(self, "_youtube_music_operation_in_progress", False))

        login_item = self.youtube_music_menu.FindItemById(self.menu_youtube_music_login_id)
        disconnect_item = self.youtube_music_menu.FindItemById(self.menu_youtube_music_disconnect_id)
        open_playlist_item = self.youtube_music_menu.FindItemById(self.menu_youtube_music_open_playlist_id)

        if login_item is not None:
            login_item.SetItemLabel("Atualizar autenticação..." if has_saved_auth else "Conectar &conta...")
            login_item.Enable(not operation_in_progress)

        if disconnect_item is not None:
            disconnect_item.Enable(has_saved_auth and not operation_in_progress)

        if open_playlist_item is not None:
            open_playlist_item.Enable(has_saved_auth and not operation_in_progress)

    def _set_youtube_music_operation_state(self, in_progress):
        self._youtube_music_operation_in_progress = bool(in_progress)
        self._refresh_youtube_music_menu_state()

    def _cancel_youtube_music_task_watchdog(self):
        watchdog = getattr(self, "_youtube_music_task_watchdog", None)
        self._youtube_music_task_watchdog = None
        if watchdog is not None:
            try:
                watchdog.Stop()
            except Exception:
                pass

    def _begin_youtube_music_busy_state(self):
        started = False
        if not wx.IsBusy():
            wx.BeginBusyCursor()
            started = True
        self._youtube_music_busy_cursor_started = started
        self._set_youtube_music_operation_state(True)

    def _end_youtube_music_busy_state(self):
        started = bool(getattr(self, "_youtube_music_busy_cursor_started", False))
        self._youtube_music_busy_cursor_started = False
        if started and wx.IsBusy():
            wx.EndBusyCursor()
        self._set_youtube_music_operation_state(False)

    def _run_youtube_music_background_task(self, worker, on_success, *, on_error=None):
        if getattr(self, "_youtube_music_operation_in_progress", False):
            self._announce("O YouTube Music já está processando uma solicitação. Aguarde um momento.")
            return False

        self._begin_youtube_music_busy_state()
        task_id = int(getattr(self, "_youtube_music_task_sequence", 0)) + 1
        self._youtube_music_task_sequence = task_id
        self._youtube_music_active_task_id = task_id
        self._cancel_youtube_music_task_watchdog()
        self._youtube_music_task_watchdog = wx.CallLater(
            self._YOUTUBE_MUSIC_BACKGROUND_TASK_TIMEOUT_MS,
            self._handle_youtube_music_background_task_timeout,
            task_id,
        )

        def runner():
            try:
                result = worker()
            except Exception as exc:
                wx.CallAfter(self._finish_youtube_music_background_task, task_id, on_success, on_error, None, exc)
                return

            wx.CallAfter(self._finish_youtube_music_background_task, task_id, on_success, on_error, result, None)

        threading.Thread(target=runner, daemon=True).start()
        return True

    def _handle_youtube_music_background_task_timeout(self, task_id):
        if task_id != getattr(self, "_youtube_music_active_task_id", None):
            return

        self._youtube_music_active_task_id = None
        self._cancel_youtube_music_task_watchdog()
        self._end_youtube_music_busy_state()
        self._announce(
            "A operação do YouTube Music demorou mais do que o esperado e foi cancelada para evitar travamento."
        )

    def _finish_youtube_music_background_task(self, task_id, on_success, on_error, result, error):
        if task_id != getattr(self, "_youtube_music_active_task_id", None):
            return

        self._youtube_music_active_task_id = None
        self._cancel_youtube_music_task_watchdog()
        self._end_youtube_music_busy_state()
        if error is not None:
            if callable(on_error):
                on_error(error)
            return

        if callable(on_success):
            on_success(result)

    def _remember_restored_youtube_music_states(self, restored_states):
        pending_states = []
        for state in restored_states or []:
            if self._youtube_music_state_needs_label_refresh(state):
                pending_states.append(state)
        self._restored_youtube_music_states_pending_refresh = pending_states

    def _youtube_music_state_needs_label_refresh(self, state):
        if not isinstance(state, PlaylistState) or not state.items:
            return False

        if not extract_playlist_id_from_source(getattr(state, "source_path", None)):
            return False

        if len(state.browser_item_labels) != len(state.items):
            return True

        return all(
            str(label or "").strip() == (os.path.basename(item) or item)
            for item, label in zip(state.items, state.browser_item_labels)
        )

    def _merge_restored_youtube_music_labels(self, state, playlist_content):
        if not isinstance(state, PlaylistState) or not state.items:
            return False

        labels_by_url = {}
        for item_url, item_label in zip(playlist_content.item_urls, playlist_content.item_labels):
            normalized_label = str(item_label or "").strip()
            if not normalized_label:
                continue
            labels_by_url.setdefault(item_url, []).append(normalized_label)

        updated_labels = []
        for index, item in enumerate(state.items):
            existing_label = state.browser_item_labels[index] if index < len(state.browser_item_labels) else ""
            matching_labels = labels_by_url.get(item)
            if matching_labels:
                updated_labels.append(matching_labels.pop(0))
                continue

            normalized_existing_label = str(existing_label or "").strip()
            updated_labels.append(normalized_existing_label or (os.path.basename(item) or item))

        if updated_labels == state.browser_item_labels:
            return False

        state.browser_item_labels = updated_labels
        state.refresh_browser_item_labels()
        return True

    def _refresh_pending_restored_youtube_music_tabs(self):
        pending_states = [
            state
            for state in getattr(self, "_restored_youtube_music_states_pending_refresh", [])
            if self._youtube_music_state_needs_label_refresh(state)
        ]
        if not pending_states:
            self._restored_youtube_music_states_pending_refresh = []
            return False

        service = self._get_youtube_music_service()

        def worker():
            refreshed_states = []
            for state in pending_states:
                playlist_id = extract_playlist_id_from_source(getattr(state, "source_path", None))
                if not playlist_id:
                    continue

                try:
                    playlist_content = service.get_playlist_content(
                        playlist_id,
                        fallback_title=state.title,
                    )
                except Exception:
                    continue

                refreshed_states.append((state, playlist_content))

            return refreshed_states

        def on_success(refreshed_states):
            self._restored_youtube_music_states_pending_refresh = []
            active_state = self._get_active_playlist_state()
            refreshed_visible_state = False

            for state, playlist_content in refreshed_states:
                if self._merge_restored_youtube_music_labels(state, playlist_content):
                    if state is active_state:
                        refreshed_visible_state = True

            if refreshed_visible_state:
                self._update_title()
                self._refresh_playlist_browser()

        def on_error(_error):
            self._restored_youtube_music_states_pending_refresh = []

        return self._run_youtube_music_background_task(worker, on_success, on_error=on_error)

    def on_connect_youtube_music(self, _event):
        service = self._get_youtube_music_service()
        dialog = YouTubeMusicBrowserAuthDialog(self)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                self._announce("Conexão com o YouTube Music cancelada.")
                return

            headers_raw = dialog.get_headers_raw()
            browser_json_path = dialog.get_browser_json_path()
        finally:
            dialog.Destroy()

        if not headers_raw and not browser_json_path:
            wx.MessageBox(
                "Cole os cabeçalhos autenticados do navegador ou selecione um browser.json, JSON de cookies ou cookies.txt válido.",
                "YouTube Music",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        try:
            saved_path = service.save_browser_auth(headers_raw=headers_raw, source_file_path=browser_json_path)
            account_name = service.get_connected_account_name()
        except Exception as exc:
            service.clear_client_cache()
            wx.MessageBox(
                f"Não foi possível conectar a conta do YouTube Music.\n\nDetalhes: {exc}",
                "YouTube Music",
                wx.OK | wx.ICON_ERROR,
                self,
            )
            self._refresh_youtube_music_menu_state()
            return

        self._refresh_youtube_music_menu_state()
        self._refresh_pending_restored_youtube_music_tabs()
        self._announce(f"Conta do YouTube Music conectada: {account_name}.")
        wx.MessageBox(
            f"Autenticação do navegador salva em:\n{saved_path}\n\nConta conectada: {account_name}",
            "YouTube Music",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def on_disconnect_youtube_music(self, _event):
        service = self._get_youtube_music_service()
        if not service.has_saved_browser_auth():
            self._announce("Nenhuma conta do YouTube Music está conectada.")
            self._refresh_youtube_music_menu_state()
            return

        with wx.MessageDialog(
            self,
            "Deseja remover a autenticação salva do YouTube Music neste computador?",
            "YouTube Music",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_YES:
                return

        service.disconnect()
        self._refresh_youtube_music_menu_state()
        self._announce("Conta do YouTube Music desconectada.")
        wx.MessageBox(
            "A autenticação salva do YouTube Music foi removida.",
            "YouTube Music",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _verify_youtube_music_connection(self):
        service = self._get_youtube_music_service()
        if not service.has_saved_browser_auth():
            self._refresh_youtube_music_menu_state()
            return

        def worker():
            return service.get_connected_account_name()

        def on_success(account_name):
            self._refresh_youtube_music_menu_state()
            if account_name:
                self._announce(f"YouTube Music reconectado: {account_name}.")
            self._refresh_pending_restored_youtube_music_tabs()

        def on_error(_error):
            service.clear_client_cache()
            self._refresh_youtube_music_menu_state()

        self._run_youtube_music_background_task(worker, on_success, on_error=on_error)

    def on_open_youtube_music_playlist(self, _event):
        service = self._get_youtube_music_service()
        if not service.has_saved_browser_auth():
            self.on_connect_youtube_music(None)
            if not service.has_saved_browser_auth():
                return

        self._announce("Buscando playlists e mixes do YouTube Music.")

        def playlists_worker():
            return service.get_library_playlists()

        def playlists_success(playlists):
            self._refresh_youtube_music_menu_state()
            if not playlists:
                wx.MessageBox(
                    "Nenhuma playlist ou mix foi encontrada na conta conectada.",
                    "YouTube Music",
                    wx.OK | wx.ICON_INFORMATION,
                    self,
                )
                return

            playlist_choices = [playlist.choice_label for playlist in playlists]
            with wx.SingleChoiceDialog(
                self,
                "Escolha a playlist ou mix do YouTube Music que deseja abrir.",
                "YouTube Music",
                playlist_choices,
            ) as dialog:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                playlist_index = dialog.GetSelection()

            if not 0 <= playlist_index < len(playlists):
                return

            self._load_youtube_music_playlist(playlists[playlist_index])

        def playlists_error(exc):
            service.clear_client_cache()
            self._refresh_youtube_music_menu_state()
            wx.MessageBox(
                f"Não foi possível listar as playlists do YouTube Music.\n\nDetalhes: {exc}",
                "YouTube Music",
                wx.OK | wx.ICON_ERROR,
                self,
            )

        self._run_youtube_music_background_task(playlists_worker, playlists_success, on_error=playlists_error)

    def _load_youtube_music_playlist(self, selected_playlist):
        service = self._get_youtube_music_service()
        self._announce(f"Carregando playlist do YouTube Music: {selected_playlist.title}.")

        def worker():
            return service.get_playlist_content(
                selected_playlist.playlist_id,
                fallback_title=selected_playlist.title,
            )

        def on_success(playlist_content):
            self._refresh_youtube_music_menu_state()
            if not playlist_content.item_urls:
                wx.MessageBox(
                    "A playlist selecionada não tem faixas reproduzíveis no momento.",
                    "YouTube Music",
                    wx.OK | wx.ICON_INFORMATION,
                    self,
                )
                return

            self._open_prepared_media_playlist(
                playlist_content.item_urls,
                playlist_content.title,
                browser_item_labels=playlist_content.item_labels,
                source_path=service.build_playlist_source(selected_playlist.playlist_id),
                announce_message=(
                    f"Playlist do YouTube Music carregada: {playlist_content.title}. "
                    f"{len(playlist_content.item_urls)} item(ns)."
                ),
            )

        def on_error(exc):
            service.clear_client_cache()
            self._refresh_youtube_music_menu_state()
            wx.MessageBox(
                f"Não foi possível carregar a playlist do YouTube Music.\n\nDetalhes: {exc}",
                "YouTube Music",
                wx.OK | wx.ICON_ERROR,
                self,
            )

        self._run_youtube_music_background_task(worker, on_success, on_error=on_error)
