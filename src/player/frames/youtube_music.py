import threading

import wx

from player.youtube_music import YouTubeMusicBrowserAuthDialog, YouTubeMusicService


class FrameYouTubeMusicMixin:
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

        def runner():
            try:
                result = worker()
            except Exception as exc:
                wx.CallAfter(self._finish_youtube_music_background_task, on_success, on_error, None, exc)
                return

            wx.CallAfter(self._finish_youtube_music_background_task, on_success, on_error, result, None)

        threading.Thread(target=runner, daemon=True).start()
        return True

    def _finish_youtube_music_background_task(self, on_success, on_error, result, error):
        self._end_youtube_music_busy_state()
        if error is not None:
            if callable(on_error):
                on_error(error)
            return

        if callable(on_success):
            on_success(result)

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
