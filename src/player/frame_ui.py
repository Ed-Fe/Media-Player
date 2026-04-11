import wx

from .accessibility import attach_named_accessible
from .constants import PROGRESS_GAUGE_RANGE, PROGRESS_TIMER_INTERVAL_MS
from .playlist_browser import PlaylistBrowserPanel


class FrameUIMixin:
    def _build_menu_bar(self):
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        self.menu_new_playlist_id = wx.NewIdRef()
        self.menu_open_file_id = wx.ID_OPEN
        self.menu_open_folder_id = wx.NewIdRef()
        self.menu_open_playlist_id = wx.NewIdRef()
        self.menu_save_playlist_id = wx.NewIdRef()
        self.recent_menu = wx.Menu()
        self.recent_files_menu = wx.Menu()
        self.recent_folders_menu = wx.Menu()
        self.recent_playlists_menu = wx.Menu()

        file_menu.Append(self.menu_new_playlist_id, "&Nova Playlist\tCtrl+T")
        file_menu.Append(self.menu_open_file_id, "Abrir &Arquivos\tCtrl+O")
        file_menu.Append(self.menu_open_folder_id, "Abrir &Pasta no Navegador\tCtrl+Shift+O")
        file_menu.Append(self.menu_open_playlist_id, "Abrir P&laylist\tCtrl+Shift+P")
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
        playback_menu.Append(self.menu_close_media_id, "Fechar Mí&dia / Aba\tCtrl+W")

        view_menu = wx.Menu()
        self.menu_playlist_browser_id = wx.NewIdRef()
        view_menu.Append(self.menu_playlist_browser_id, "Modo &Itens / Player\tF6")

        tabs_menu = wx.Menu()
        self.menu_next_tab_id = wx.NewIdRef()
        self.menu_previous_tab_id = wx.NewIdRef()
        tabs_menu.Append(self.menu_next_tab_id, "Próxima A&ba\tCtrl+Tab")
        tabs_menu.Append(self.menu_previous_tab_id, "Aba A&nterior\tCtrl+Shift+Tab")

        settings_menu = wx.Menu()
        self.menu_check_updates_id = wx.NewIdRef()
        self.menu_preferences_id = wx.NewIdRef()
        settings_menu.Append(self.menu_check_updates_id, "Verificar &atualizações")
        settings_menu.AppendSeparator()
        settings_menu.Append(self.menu_preferences_id, "&Preferências\tCtrl+,")

        menu_bar.Append(file_menu, "&Arquivo")
        menu_bar.Append(playback_menu, "&Reprodução")
        menu_bar.Append(view_menu, "&Exibir")
        menu_bar.Append(tabs_menu, "A&bas")
        menu_bar.Append(settings_menu, "Con&figurações")
        self.SetMenuBar(menu_bar)
        self._refresh_recent_menus()

    def _build_ui(self):
        panel = wx.Panel(self)
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(panel)
        self.progress_panel = wx.Panel(panel)
        self.progress_label = wx.StaticText(self.progress_panel, label="Tempo: nenhuma mídia carregada.")
        self.progress_gauge = wx.Gauge(self.progress_panel, range=PROGRESS_GAUGE_RANGE, style=wx.GA_SMOOTH)
        self.progress_timer = wx.Timer(self)

        progress_sizer = wx.BoxSizer(wx.VERTICAL)
        progress_sizer.Add(self.progress_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)
        progress_sizer.Add(self.progress_gauge, 0, wx.ALL | wx.EXPAND, 10)
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

        root_sizer.Add(self.notebook, 1, wx.EXPAND)
        root_sizer.Add(self.progress_panel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 4)
        panel.SetSizer(root_sizer)

        self._create_empty_playlist_tab(select=True)
        self.player.audio_set_volume(self.current_volume)
        self._update_time_bar()

    def _bind_events(self):
        self.Bind(wx.EVT_MENU, self.on_new_playlist, id=self.menu_new_playlist_id)
        self.Bind(wx.EVT_MENU, self.on_open, id=self.menu_open_file_id)
        self.Bind(wx.EVT_MENU, self.on_open_folder, id=self.menu_open_folder_id)
        self.Bind(wx.EVT_MENU, self.on_open_playlist, id=self.menu_open_playlist_id)
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
        self.Bind(wx.EVT_MENU, self.on_toggle_playlist_browser, id=self.menu_playlist_browser_id)
        self.Bind(wx.EVT_MENU, self.on_next_tab, id=self.menu_next_tab_id)
        self.Bind(wx.EVT_MENU, self.on_previous_tab, id=self.menu_previous_tab_id)
        self.Bind(wx.EVT_MENU, self.on_check_for_updates, id=self.menu_check_updates_id)
        self.Bind(wx.EVT_MENU, self.on_open_preferences, id=self.menu_preferences_id)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
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

        root_sizer.Add(browser_panel, 0, wx.EXPAND | wx.ALL, 4)
        root_sizer.Add(video_panel, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 4)
        page.SetSizer(root_sizer)
        page.browser_panel = browser_panel
        page.video_panel = video_panel
        return page
