import wx

from ..accessibility import attach_named_accessible


class YouTubeMusicTabPanel(wx.Panel):
	def __init__(
		self,
		parent,
		*,
		on_connect,
		on_disconnect,
		on_refresh_library,
		on_open_selected,
		on_open_manual_source,
	):
		super().__init__(parent, style=wx.TAB_TRAVERSAL)

		self._all_playlists = []
		self._visible_playlists = []
		self._visible_playlist_ids = []
		self._updating_controls = False
		self._on_connect = on_connect
		self._on_disconnect = on_disconnect
		self._on_refresh_library = on_refresh_library
		self._on_open_selected = on_open_selected
		self._on_open_manual_source = on_open_manual_source

		root_sizer = wx.BoxSizer(wx.VERTICAL)

		intro_label = wx.StaticText(
			self,
			label=(
				"Abra sua central do YouTube Music em uma aba dedicada. "
				"Conecte ou atualize o acesso da conta, atualize a biblioteca, filtre playlists e mixes, "
				"ou abra uma playlist específica pelo link ou ID."
			),
		)
		intro_label.Wrap(640)
		root_sizer.Add(intro_label, 0, wx.ALL | wx.EXPAND, 10)

		status_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Conta e biblioteca"), wx.VERTICAL)
		self.connection_label = wx.StaticText(self, label="Conta: não conectada")
		self.connection_label.SetName("Status da conta do YouTube Music")
		self.connection_label.SetHelpText("Informa se existe uma conta do YouTube Music conectada nesta instalação.")
		self.library_summary_label = wx.StaticText(self, label="Biblioteca: nenhuma playlist carregada.")
		self.library_summary_label.SetName("Resumo da biblioteca do YouTube Music")
		self.library_summary_label.SetHelpText("Resume quantas playlists ou mixes estão disponíveis na aba do YouTube Music.")
		self.status_message_label = wx.StaticText(self, label="")
		self.status_message_label.SetName("Mensagem da central do YouTube Music")
		self.status_message_label.SetHelpText("Mostra o resultado da última atualização da biblioteca ou do acesso do YouTube Music.")
		self.status_message_label.Wrap(620)

		attach_named_accessible(
			self.connection_label,
			name="Status da conta do YouTube Music",
			description="Informa se existe uma conta do YouTube Music conectada nesta instalação.",
			value_provider=lambda: self.connection_label.GetLabel(),
		)
		attach_named_accessible(
			self.library_summary_label,
			name="Resumo da biblioteca do YouTube Music",
			description="Resume quantas playlists ou mixes estão disponíveis na aba do YouTube Music.",
			value_provider=lambda: self.library_summary_label.GetLabel(),
		)
		attach_named_accessible(
			self.status_message_label,
			name="Mensagem da central do YouTube Music",
			description="Mostra o resultado da última atualização da biblioteca ou do acesso do YouTube Music.",
			value_provider=lambda: self.status_message_label.GetLabel(),
		)

		status_box.Add(self.connection_label, 0, wx.ALL | wx.EXPAND, 6)
		status_box.Add(self.library_summary_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
		status_box.Add(self.status_message_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)

		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.connect_button = wx.Button(self, label="Conectar conta...")
		self.disconnect_button = wx.Button(self, label="Desconectar conta")
		self.refresh_button = wx.Button(self, label="Atualizar biblioteca")
		self.open_selected_button = wx.Button(self, label="Abrir seleção")

		for button, name, description in (
			(
				self.connect_button,
				"Conectar ou atualizar acesso do YouTube Music",
				"Abre o diálogo para conectar uma conta do YouTube Music ou atualizar a autenticação salva.",
			),
			(
				self.disconnect_button,
				"Desconectar conta do YouTube Music",
				"Remove a autenticação salva da conta do YouTube Music nesta instalação.",
			),
			(
				self.refresh_button,
				"Atualizar biblioteca do YouTube Music",
				"Busca novamente as playlists e mixes disponíveis na conta conectada.",
			),
			(
				self.open_selected_button,
				"Abrir playlist selecionada do YouTube Music",
				"Abre a playlist ou mix atualmente selecionada na lista da aba do YouTube Music.",
			),
		):
			button.SetName(name)
			button.SetHelpText(description)
			button.SetToolTip(description)
			button_sizer.Add(button, 0, wx.RIGHT, 8)

		status_box.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 6)
		root_sizer.Add(status_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

		manual_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Abrir playlist específica"), wx.VERTICAL)
		manual_intro = wx.StaticText(
			self,
			label="Cole um link do YouTube Music/YouTube ou informe apenas o ID da playlist ou mix.",
		)
		manual_intro.Wrap(620)
		self.manual_source_ctrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		self.manual_source_ctrl.SetName("Link ou ID da playlist do YouTube Music")
		self.manual_source_ctrl.SetHelpText(
			"Cole um link de playlist ou mix do YouTube Music, ou informe diretamente o ID que deseja abrir."
		)
		self.manual_open_button = wx.Button(self, label="Abrir pelo link ou ID")
		self.manual_open_button.SetName("Abrir playlist específica do YouTube Music")
		self.manual_open_button.SetHelpText(
			"Abre a playlist ou mix informada no campo acima, usando um link do YouTube Music ou um ID direto."
		)
		self.manual_open_button.SetToolTip(self.manual_open_button.GetHelpText())

		manual_box.Add(manual_intro, 0, wx.ALL | wx.EXPAND, 6)
		manual_box.Add(self.manual_source_ctrl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
		manual_box.Add(self.manual_open_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_LEFT, 6)
		root_sizer.Add(manual_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

		library_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Playlists e mixes"), wx.VERTICAL)
		filter_label = wx.StaticText(self, label="Filtro:")
		self.filter_ctrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		self.filter_ctrl.SetName("Filtro da biblioteca do YouTube Music")
		self.filter_ctrl.SetHelpText(
			"Filtra a lista por título, tipo da lista ou quantidade de faixas, sem abrir mão do teclado."
		)
		self.results_label = wx.StaticText(self, label="Mostrando 0 de 0 resultados.")
		self.results_label.SetName("Contagem de resultados do YouTube Music")
		self.results_label.SetHelpText("Informa quantas playlists ou mixes aparecem após o filtro aplicado.")
		self.playlists_list = wx.ListBox(self)
		self.playlists_list.SetName("Lista de playlists do YouTube Music")
		self.playlists_list.SetHelpText(
			"Mostra as playlists e mixes disponíveis. Use setas para navegar, Enter para abrir e Tab para sair da aba."
		)
		help_label = wx.StaticText(
			self,
			label="Enter abre a seleção atual. Esc fecha a aba. Tab volta para a navegação padrão entre controles da tela.",
		)
		help_label.Wrap(620)

		library_box.Add(filter_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 6)
		library_box.Add(self.filter_ctrl, 0, wx.ALL | wx.EXPAND, 6)
		library_box.Add(self.results_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
		library_box.Add(self.playlists_list, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
		library_box.Add(help_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
		root_sizer.Add(library_box, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

		self.SetSizer(root_sizer)

		self.connect_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_connect())
		self.disconnect_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_disconnect())
		self.refresh_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_refresh_library())
		self.open_selected_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_open_selected())
		self.manual_open_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_open_manual_source())
		self.manual_source_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_manual_source_enter)
		self.filter_ctrl.Bind(wx.EVT_TEXT, self._on_filter_changed)
		self.filter_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_filter_text_enter)
		self.playlists_list.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
		self.playlists_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_open_selected_event)
		self.playlists_list.Bind(wx.EVT_CHAR_HOOK, self._on_list_key_down)

		self._refresh_playlist_list()
		self._update_action_state(connected=False, operation_in_progress=False)

	def _normalized_filter_text(self):
		return str(self.filter_ctrl.GetValue() or "").strip().casefold()

	def _filtered_playlists(self):
		filter_text = self._normalized_filter_text()
		if not filter_text:
			return list(self._all_playlists)

		filtered = []
		for playlist in self._all_playlists:
			haystack = " ".join(
				part
				for part in (
					getattr(playlist, "title", ""),
					getattr(playlist, "track_count_text", ""),
					getattr(playlist, "source_badge", ""),
					getattr(playlist, "choice_label", ""),
				)
				if part
			).casefold()
			if filter_text in haystack:
				filtered.append(playlist)

		return filtered

	def _refresh_playlist_list(self, selected_playlist_id=None):
		if selected_playlist_id is None:
			selected_playlist_id = self.get_selected_playlist_id()

		self._visible_playlists = self._filtered_playlists()
		self._visible_playlist_ids = [playlist.playlist_id for playlist in self._visible_playlists]

		labels = [playlist.choice_label for playlist in self._visible_playlists]
		self.playlists_list.Set(labels)

		selection_index = wx.NOT_FOUND
		if selected_playlist_id and selected_playlist_id in self._visible_playlist_ids:
			selection_index = self._visible_playlist_ids.index(selected_playlist_id)
		elif labels:
			selection_index = 0

		if selection_index != wx.NOT_FOUND:
			self.playlists_list.SetSelection(selection_index)

		self.results_label.SetLabel(
			f"Mostrando {len(self._visible_playlists)} de {len(self._all_playlists)} playlists e mixes."
		)
		self._update_selection_actions()

	def _update_selection_actions(self):
		has_selection = self.get_selected_playlist_id() is not None
		self.open_selected_button.Enable(has_selection and self.open_selected_button.IsEnabled())

	def _update_action_state(self, *, connected, operation_in_progress):
		self.connect_button.SetLabel("Atualizar acesso..." if connected else "Conectar conta...")
		self.connect_button.Enable(not operation_in_progress)
		self.disconnect_button.Enable(connected and not operation_in_progress)
		self.refresh_button.Enable(connected and not operation_in_progress)
		self.manual_open_button.Enable(not operation_in_progress)
		self.manual_source_ctrl.Enable(not operation_in_progress)
		self.filter_ctrl.Enable(True)
		can_open_selected = connected and not operation_in_progress and self.get_selected_playlist_id() is not None
		self.open_selected_button.Enable(can_open_selected)
		self.playlists_list.Enable(True)

	def update_view(
		self,
		*,
		connected,
		account_name,
		playlists,
		operation_in_progress,
		status_message,
	):
		self.Freeze()
		try:
			selected_playlist_id = self.get_selected_playlist_id()
			self._all_playlists = list(playlists or [])
			self.connection_label.SetLabel(
				f"Conta: {account_name}." if connected and account_name else "Conta: não conectada."
			)
			if connected:
				self.library_summary_label.SetLabel(
					f"Biblioteca: {len(self._all_playlists)} playlist(s) e mix(es) disponíveis."
				)
			else:
				self.library_summary_label.SetLabel("Biblioteca: conecte uma conta para listar playlists e mixes.")

			self.status_message_label.SetLabel(str(status_message or "").strip())
			self.status_message_label.Wrap(620)
			self._refresh_playlist_list(selected_playlist_id=selected_playlist_id)
			self._update_action_state(connected=connected, operation_in_progress=operation_in_progress)
			self.Layout()
		finally:
			self.Thaw()

	def get_selected_playlist_id(self):
		selection = self.playlists_list.GetSelection()
		if selection == wx.NOT_FOUND or not 0 <= selection < len(self._visible_playlist_ids):
			return None
		return self._visible_playlist_ids[selection]

	def get_manual_source(self):
		return str(self.manual_source_ctrl.GetValue() or "").strip()

	def clear_manual_source(self):
		self.manual_source_ctrl.SetValue("")

	def _on_filter_changed(self, _event):
		self._refresh_playlist_list()

	def _on_filter_text_enter(self, _event):
		if self.get_selected_playlist_id() is not None:
			self._on_open_selected()

	def _on_selection_changed(self, _event):
		self._update_selection_actions()

	def _on_open_selected_event(self, _event):
		if self.get_selected_playlist_id() is not None:
			self._on_open_selected()

	def _on_manual_source_enter(self, _event):
		self._on_open_manual_source()

	def _on_list_key_down(self, event):
		key_code = event.GetKeyCode()
		if key_code == wx.WXK_TAB:
			event.Skip()
			return

		if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			if self.get_selected_playlist_id() is not None:
				self._on_open_selected()
				return

		event.Skip()
