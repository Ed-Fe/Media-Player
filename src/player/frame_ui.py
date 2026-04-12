import wx

from .accessibility import attach_named_accessible
from .constants import PROGRESS_GAUGE_RANGE, PROGRESS_TIMER_INTERVAL_MS
from .playlist_browser import PlaylistBrowserPanel


class FrameUIMixin:
    def _primary_shortcuts_hint_text(self):
        return (
            "Atalhos principais: Ctrl+Alt+O abrir mídia, playlist ou pasta · Ctrl+O abrir arquivos ou playlist · Ctrl+Shift+O abrir pasta · "
            "Espaço reproduzir/pausar · ←/→ buscar · ↑/↓ volume · F6 itens/player · F1 ajuda"
        )

    def _player_overlay_hint_text(self):
        return (
            "Sem mídia carregada\n\n"
            "Ctrl+Alt+O abre mídia, playlist ou pasta\n"
            "Ctrl+O abre arquivos ou playlist\n"
            "Ctrl+Shift+O abre uma pasta no navegador\n"
            "Espaço reproduz ou pausa\n"
            "F6 alterna entre itens e player\n"
            "F1 mostra a ajuda rápida de atalhos"
        )

    def _keyboard_help_text(self):
        return (
            "Ajuda rápida de atalhos\n\n"
            "Arquivos e playlists\n"
            "Ctrl+Alt+O — Abrir mídia, playlist ou pasta\n"
            "Ctrl+O — Abrir arquivos de mídia ou uma playlist local\n"
            "Ctrl+Shift+O — Abrir pasta no navegador\n"
            "Ctrl+Shift+S — Salvar playlist atual\n"
            "Ctrl+T — Nova playlist\n"
            "Ctrl+W — Fechar mídia atual ou aba vazia\n"
            "Ctrl+Shift+W — Fechar aba ou playlist atual\n\n"
            "Reprodução\n"
            "Espaço — Play/Pause\n"
            "Seta esquerda / direita — Voltar ou avançar no arquivo\n"
            "Home / End — Ir para o início ou para o fim\n"
            "Seta cima / baixo — Aumentar ou diminuir o volume\n"
            "Ctrl+PageUp / Ctrl+PageDown — Faixa anterior ou próxima\n"
            "E — Alternar modo aleatório\n"
            "R — Alternar modo de repetição\n"
            "T — Anunciar tempo\n"
            "V — Anunciar volume\n"
            "S — Anunciar status\n\n"
            "Navegação\n"
            "F6 — Alternar entre a lista de itens e o player\n"
            "Enter — Tocar ou abrir o item selecionado no navegador\n"
            "Delete — Remover item da playlist\n"
            "Backspace — Voltar de pasta no navegador\n"
            "Digite letras ou números — Ir rapidamente para itens com esse início\n"
            "Ctrl+Tab / Ctrl+Shift+Tab — Próxima ou aba anterior\n"
            "F1 — Mostrar esta ajuda"
        )

    def _refresh_shortcuts_hint_layout(self):
        if not hasattr(self, "shortcuts_hint_label") or not hasattr(self, "progress_panel"):
            return

        wrap_width = max(320, self.progress_panel.GetClientSize().Width - 24)
        self.shortcuts_hint_label.Wrap(wrap_width)
        self.progress_panel.Layout()

    def _refresh_player_visual_hints(self):
        if not hasattr(self, "notebook"):
            return

        for index in range(self.notebook.GetPageCount()):
            page = self.notebook.GetPage(index)
            video_panel = getattr(page, "video_panel", None)
            video_hint_overlay = getattr(page, "video_hint_overlay", None)
            if not video_panel or not video_hint_overlay:
                continue

            playlist_state = self._get_playlist_state(index)
            show_overlay = bool(playlist_state and not playlist_state.current_media_path)
            needs_layout = video_hint_overlay.IsShown() != show_overlay
            if needs_layout:
                video_hint_overlay.Show(show_overlay)

            if show_overlay:
                wrap_width = max(260, video_panel.GetClientSize().Width - 80)
                if getattr(page, "video_hint_wrap_width", None) != wrap_width:
                    video_hint_overlay.Wrap(wrap_width)
                    page.video_hint_wrap_width = wrap_width
                    needs_layout = True

            if needs_layout:
                video_panel.Layout()

    def _on_progress_panel_size(self, event):
        self._refresh_shortcuts_hint_layout()
        event.Skip()

    def _show_keyboard_help_dialog(self):
        dialog = wx.Dialog(
            self,
            title="Ajuda rápida de atalhos",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dialog.SetMinSize((520, 420))

        root_sizer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.TextCtrl(
            dialog,
            value=self._keyboard_help_text(),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        instructions.SetName("Ajuda rápida de atalhos")
        instructions.SetHelpText("Lista os atalhos principais do player e do navegador de itens.")
        instructions.SetInsertionPoint(0)

        button_sizer = dialog.CreateStdDialogButtonSizer(wx.OK)
        if button_sizer is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetLabel("F&echar")

        root_sizer.Add(instructions, 1, wx.ALL | wx.EXPAND, 12)
        if button_sizer is not None:
            root_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, 12)

        dialog.SetSizerAndFit(root_sizer)
        dialog.SetSize((560, 460))
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()

    def _build_menu_bar(self):
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        self.menu_new_playlist_id = wx.NewIdRef()
        self.menu_open_file_id = wx.ID_OPEN
        self.menu_open_folder_id = wx.NewIdRef()
        self.menu_open_source_id = wx.NewIdRef()
        self.menu_save_playlist_id = wx.NewIdRef()
        self.recent_menu = wx.Menu()
        self.recent_files_menu = wx.Menu()
        self.recent_folders_menu = wx.Menu()
        self.recent_playlists_menu = wx.Menu()

        file_menu.Append(self.menu_new_playlist_id, "&Nova Playlist\tCtrl+T")
        file_menu.Append(self.menu_open_source_id, "Abrir &Mídia, Playlist ou Pasta...\tCtrl+Alt+O")
        file_menu.Append(self.menu_save_playlist_id, "Salvar Playli&st\tCtrl+Shift+S")
        self.recent_menu.AppendSubMenu(self.recent_files_menu, "Arquivos recentes")
        self.recent_menu.AppendSubMenu(self.recent_folders_menu, "Pastas recentes")
        self.recent_menu.AppendSubMenu(self.recent_playlists_menu, "Playlists recentes")
        file_menu.AppendSubMenu(self.recent_menu, "&Recentes")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "&Sair\tAlt+F4")

        playback_menu = wx.Menu()
        self.menu_previous_track_id = wx.NewIdRef()
        self.menu_play_pause_id = wx.NewIdRef()
        self.menu_stop_id = wx.NewIdRef()
        self.menu_next_track_id = wx.NewIdRef()
        self.menu_close_media_id = wx.NewIdRef()
        self.menu_close_tab_id = wx.NewIdRef()
        self.menu_open_equalizer_id = wx.NewIdRef()
        self.menu_toggle_shuffle_id = wx.NewIdRef()
        self.menu_cycle_repeat_id = wx.NewIdRef()
        self.menu_announce_time_id = wx.NewIdRef()
        self.menu_announce_volume_id = wx.NewIdRef()
        self.menu_announce_status_id = wx.NewIdRef()
        playback_menu.Append(self.menu_previous_track_id, "Faixa &Anterior\tCtrl+PageUp")
        playback_menu.Append(self.menu_play_pause_id, "&Play/Pause (Espaço)")
        playback_menu.Append(self.menu_stop_id, "S&top\tCtrl+.")
        playback_menu.Append(self.menu_next_track_id, "Próxima Fai&xa\tCtrl+PageDown")
        playback_menu.AppendSeparator()
        playback_menu.Append(self.menu_open_equalizer_id, "Eq&ualizador por aba\tCtrl+Shift+E")
        playback_menu.AppendSeparator()
        playback_menu.Append(self.menu_toggle_shuffle_id, "Em&baralhar (E)")
        playback_menu.Append(self.menu_cycle_repeat_id, "Modo de &Repetição (R)")
        playback_menu.Append(self.menu_announce_time_id, "Anunciar &Tempo (T)")
        playback_menu.Append(self.menu_announce_volume_id, "Anunciar &Volume (V)")
        playback_menu.Append(self.menu_announce_status_id, "Anunciar &Status (S)")
        playback_menu.AppendSeparator()
        playback_menu.Append(self.menu_close_media_id, "Fechar Mí&dia / Aba vazia\tCtrl+W")
        playback_menu.Append(self.menu_close_tab_id, "Fechar A&ba / Playlist\tCtrl+Shift+W")

        view_menu = wx.Menu()
        self.menu_playlist_browser_id = wx.NewIdRef()
        view_menu.Append(self.menu_playlist_browser_id, "Modo &Itens / Player\tF6")

        tabs_menu = wx.Menu()
        self.menu_next_tab_id = wx.NewIdRef()
        self.menu_previous_tab_id = wx.NewIdRef()
        tabs_menu.Append(self.menu_next_tab_id, "Próxima A&ba\tCtrl+Tab")
        tabs_menu.Append(self.menu_previous_tab_id, "Aba A&nterior\tCtrl+Shift+Tab")
        tabs_menu.AppendSeparator()
        tabs_menu.Append(self.menu_close_tab_id, "Fechar A&ba atual\tCtrl+Shift+W")

        settings_menu = wx.Menu()
        self.menu_check_updates_id = wx.NewIdRef()
        self.menu_preferences_id = wx.NewIdRef()
        settings_menu.Append(self.menu_check_updates_id, "Verificar &atualizações")
        settings_menu.AppendSeparator()
        settings_menu.Append(self.menu_preferences_id, "&Preferências\tCtrl+,")

        help_menu = wx.Menu()
        self.menu_keyboard_help_id = wx.NewIdRef()
        help_menu.Append(self.menu_keyboard_help_id, "Ajuda rápida de &atalhos\tF1")

        menu_bar.Append(file_menu, "&Arquivo")
        menu_bar.Append(playback_menu, "&Reprodução")
        menu_bar.Append(view_menu, "&Exibir")
        menu_bar.Append(tabs_menu, "A&bas")
        menu_bar.Append(settings_menu, "Con&figurações")
        menu_bar.Append(help_menu, "A&juda")
        self.SetMenuBar(menu_bar)
        self._refresh_recent_menus()

    def _build_ui(self):
        panel = wx.Panel(self)
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(panel)
        self.progress_panel = wx.Panel(panel)
        self.progress_label = wx.StaticText(self.progress_panel, label="Tempo: nenhuma mídia carregada.")
        self.progress_gauge = wx.Gauge(self.progress_panel, range=PROGRESS_GAUGE_RANGE, style=wx.GA_SMOOTH)
        self.shortcuts_hint_label = wx.StaticText(
            self.progress_panel,
            label=self._primary_shortcuts_hint_text(),
        )
        self.progress_timer = wx.Timer(self)

        progress_sizer = wx.BoxSizer(wx.VERTICAL)
        progress_sizer.Add(self.progress_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)
        progress_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 10)
        progress_sizer.Add(self.shortcuts_hint_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        self.progress_panel.SetSizer(progress_sizer)

        self.progress_panel.SetName("Painel de tempo")
        self.progress_panel.SetHelpText(
            "Mostra o andamento da mídia atual com o tempo decorrido e a duração total quando disponível."
        )
        self.progress_label.SetName("Tempo da mídia")
        self.progress_label.SetHelpText(
            "Mostra o tempo decorrido e o tempo total da mídia atual."
        )
        self.progress_gauge.SetName("Barra de tempo")
        self.progress_gauge.SetHelpText(
            "Mostra visualmente o andamento da mídia atual sem alterar o foco do teclado."
        )
        self.shortcuts_hint_label.SetName("Dicas rápidas de atalhos")
        self.shortcuts_hint_label.SetHelpText(
            "Resume os atalhos mais usados para abrir mídia, controlar a reprodução e acessar a ajuda."
        )
        self.shortcuts_hint_label.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        attach_named_accessible(
            self.progress_label,
            name="Tempo da mídia",
            description="Mostra o tempo decorrido e a duração total da mídia atual.",
            value_provider=lambda: self.progress_label.GetLabel(),
        )
        attach_named_accessible(
            self.progress_gauge,
            name="Barra de tempo",
            description="Mostra o progresso da mídia atual.",
            value_provider=self._time_bar_accessible_value,
        )
        attach_named_accessible(
            self.shortcuts_hint_label,
            name="Dicas rápidas de atalhos",
            description="Resume os atalhos mais usados para controlar o player.",
            value_provider=lambda: self.shortcuts_hint_label.GetLabel(),
        )

        root_sizer.Add(self.notebook, 1, wx.EXPAND)
        root_sizer.Add(self.progress_panel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 4)
        panel.SetSizer(root_sizer)

        self._create_empty_playlist_tab(select=True)
        self.player.audio_set_volume(self.current_volume)
        self._update_time_bar()
        self._refresh_shortcuts_hint_layout()

    def _bind_events(self):
        accelerators = wx.AcceleratorTable(
            [
                (wx.ACCEL_CTRL, ord("O"), self.menu_open_file_id),
                (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("O"), int(self.menu_open_folder_id)),
                (wx.ACCEL_CTRL | wx.ACCEL_ALT, ord("O"), int(self.menu_open_source_id)),
            ]
        )
        self.SetAcceleratorTable(accelerators)

        self.Bind(wx.EVT_MENU, self.on_new_playlist, id=self.menu_new_playlist_id)
        self.Bind(wx.EVT_MENU, self.on_open, id=self.menu_open_file_id)
        self.Bind(wx.EVT_MENU, self.on_open_folder, id=self.menu_open_folder_id)
        self.Bind(wx.EVT_MENU, self.on_open_source, id=self.menu_open_source_id)
        self.Bind(wx.EVT_MENU, self.on_save_playlist, id=self.menu_save_playlist_id)
        self.Bind(wx.EVT_MENU, self.on_previous_track, id=self.menu_previous_track_id)
        self.Bind(wx.EVT_MENU, self.on_play_pause, id=self.menu_play_pause_id)
        self.Bind(wx.EVT_MENU, self.on_stop, id=self.menu_stop_id)
        self.Bind(wx.EVT_MENU, self.on_next_track, id=self.menu_next_track_id)
        self.Bind(wx.EVT_MENU, self.on_open_equalizer, id=self.menu_open_equalizer_id)
        self.Bind(wx.EVT_MENU, self.on_toggle_shuffle, id=self.menu_toggle_shuffle_id)
        self.Bind(wx.EVT_MENU, self.on_cycle_repeat_mode, id=self.menu_cycle_repeat_id)
        self.Bind(wx.EVT_MENU, self.on_announce_time, id=self.menu_announce_time_id)
        self.Bind(wx.EVT_MENU, self.on_announce_volume, id=self.menu_announce_volume_id)
        self.Bind(wx.EVT_MENU, self.on_announce_status, id=self.menu_announce_status_id)
        self.Bind(wx.EVT_MENU, self.on_close_current_media, id=self.menu_close_media_id)
        self.Bind(wx.EVT_MENU, self.on_close_current_tab, id=self.menu_close_tab_id)
        self.Bind(wx.EVT_MENU, self.on_toggle_playlist_browser, id=self.menu_playlist_browser_id)
        self.Bind(wx.EVT_MENU, self.on_next_tab, id=self.menu_next_tab_id)
        self.Bind(wx.EVT_MENU, self.on_previous_tab, id=self.menu_previous_tab_id)
        self.Bind(wx.EVT_MENU, self.on_check_for_updates, id=self.menu_check_updates_id)
        self.Bind(wx.EVT_MENU, self.on_open_preferences, id=self.menu_preferences_id)
        self.Bind(wx.EVT_MENU, self.on_show_keyboard_help, id=self.menu_keyboard_help_id)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        self.progress_panel.Bind(wx.EVT_SIZE, self._on_progress_panel_size)
        self.Bind(wx.EVT_TIMER, self.on_progress_timer, self.progress_timer)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.progress_timer.Start(PROGRESS_TIMER_INTERVAL_MS)

    def _create_playlist_page(self):
        page = wx.Panel(self.notebook)
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)

        browser_panel = PlaylistBrowserPanel(
            page,
            on_activate_item=self.on_playlist_browser_activate_item,
            on_remove_item=self.on_playlist_browser_remove_item,
            on_preview_item=self.on_playlist_browser_preview_item,
            on_go_back=self.on_playlist_browser_go_back,
            on_toggle_navigation_mode=self.on_toggle_playlist_browser,
        )

        video_panel = wx.Panel(page)
        video_panel.SetName("Painel de vídeo")
        video_panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        video_panel.Bind(wx.EVT_SIZE, self.on_video_panel_resize)
        video_panel.Bind(wx.EVT_SET_FOCUS, self.on_video_panel_focus)

        video_hint_overlay = wx.StaticText(
            video_panel,
            label=self._player_overlay_hint_text(),
            style=wx.ALIGN_CENTER_HORIZONTAL,
        )
        video_hint_overlay.SetName("Ajuda visual do player")
        video_hint_overlay.SetHelpText(
            "Mostra os atalhos principais quando não há mídia carregada na aba atual."
        )
        video_hint_overlay.SetForegroundColour(wx.Colour(235, 235, 235))

        video_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        video_panel_sizer.AddStretchSpacer()
        video_panel_sizer.Add(video_hint_overlay, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL, 24)
        video_panel_sizer.AddStretchSpacer()
        video_panel.SetSizer(video_panel_sizer)

        root_sizer.Add(browser_panel, 0, wx.EXPAND | wx.ALL, 4)
        root_sizer.Add(video_panel, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 4)
        page.SetSizer(root_sizer)
        page.browser_panel = browser_panel
        page.video_panel = video_panel
        page.video_hint_overlay = video_hint_overlay
        page.video_hint_wrap_width = None
        return page
