from dataclasses import replace

import wx

from .constants import MAX_CROSSFADE_SECONDS, REPEAT_MODE_LABELS, REPEAT_MODES


class PreferencesDialog(wx.Dialog):
    def __init__(self, parent, settings):
        super().__init__(
            parent,
            title="Preferências",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self._settings = settings

        panel = wx.Panel(self)
        root_sizer = wx.BoxSizer(wx.VERTICAL)

        intro_label = wx.StaticText(
            panel,
            label="Ajuste como o player inicia, salva estado e responde aos atalhos. "
            "Use as guias para navegar entre as categorias. Pressione Esc para cancelar ou Enter em Salvar para confirmar.",
        )
        intro_label.Wrap(540)

        root_sizer.Add(intro_label, 0, wx.ALL | wx.EXPAND, 10)

        self.notebook = wx.Notebook(panel)
        self.notebook.SetName("Categorias de preferências")
        self.notebook.SetHelpText("Use as guias Geral, Reprodução e Acessibilidade para navegar pelas configurações.")

        self._build_general_tab()
        self._build_playback_tab()
        self._build_accessibility_tab()

        root_sizer.Add(self.notebook, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        button_sizer = wx.StdDialogButtonSizer()
        self.save_button = wx.Button(panel, wx.ID_OK, "&Salvar")
        self.cancel_button = wx.Button(panel, wx.ID_CANCEL, "&Cancelar")
        self.save_button.SetDefault()
        button_sizer.AddButton(self.save_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()
        root_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(root_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(frame_sizer)
        self.SetMinSize((620, 480))
        self.SetEscapeId(wx.ID_CANCEL)

        self._populate_controls(settings)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

    def _build_general_tab(self):
        page, page_sizer = self._create_tab_page("Geral")

        info_label = wx.StaticText(
            page,
            label="Configurações relacionadas ao início do player, à sessão salva e ao comportamento ao sair.",
        )
        info_label.Wrap(520)

        general_box = wx.StaticBoxSizer(wx.StaticBox(page, label="Inicialização e sessão"), wx.VERTICAL)
        self.restore_session_checkbox = wx.CheckBox(page, label="&Restaurar sessão ao iniciar")
        self.remember_window_size_checkbox = wx.CheckBox(page, label="Lembrar tamanho da &janela")
        self.remember_last_folder_checkbox = wx.CheckBox(page, label="Lembrar última &pasta usada")
        self.confirm_on_exit_checkbox = wx.CheckBox(page, label="Con&firmar ao sair")

        self._configure_checkbox(
            self.restore_session_checkbox,
            "Restaurar sessão ao iniciar",
            "Reabre as abas e tenta retomar a última sessão salva ao iniciar o player.",
        )
        self._configure_checkbox(
            self.remember_window_size_checkbox,
            "Lembrar tamanho da janela",
            "Salva e restaura o tamanho da janela principal entre execuções.",
        )
        self._configure_checkbox(
            self.remember_last_folder_checkbox,
            "Lembrar última pasta usada",
            "Usa a última pasta aberta como diretório inicial nos diálogos de abrir e salvar.",
        )
        self._configure_checkbox(
            self.confirm_on_exit_checkbox,
            "Confirmar ao sair",
            "Pede confirmação antes de fechar o player.",
        )

        for control in (
            self.restore_session_checkbox,
            self.remember_window_size_checkbox,
            self.remember_last_folder_checkbox,
            self.confirm_on_exit_checkbox,
        ):
            general_box.Add(control, 0, wx.ALL | wx.EXPAND, 6)

        note_label = wx.StaticText(
            page,
            label="As mudanças de restauração de sessão e de tamanho da janela afetam principalmente as próximas aberturas do player.",
        )
        note_label.Wrap(520)

        page_sizer.Add(info_label, 0, wx.ALL | wx.EXPAND, 10)
        page_sizer.Add(general_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        page_sizer.Add(note_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        self.notebook.AddPage(page, "Geral", select=True)

    def _build_playback_tab(self):
        page, page_sizer = self._create_tab_page("Reprodução")

        info_label = wx.StaticText(
            page,
            label="Configurações ligadas ao volume, ao avanço na mídia e ao comportamento padrão de playlists novas.",
        )
        info_label.Wrap(520)

        playback_box = wx.StaticBoxSizer(wx.StaticBox(page, label="Controles de reprodução"), wx.VERTICAL)
        self.shuffle_new_playlists_checkbox = wx.CheckBox(page, label="Ativar e&mbaralhamento em novas playlists")
        self._configure_checkbox(
            self.shuffle_new_playlists_checkbox,
            "Ativar embaralhamento em novas playlists",
            "Ativa o modo aleatório automaticamente em playlists criadas depois de salvar as preferências.",
        )

        volume_group, self.default_volume_ctrl = self._build_spin_control_group(
            page,
            label_text="Volume padrão",
            help_text="Define o volume inicial do player. 0 é mudo e 100 é o máximo.",
            min_value=0,
            max_value=100,
        )
        volume_step_group, self.volume_step_ctrl = self._build_spin_control_group(
            page,
            label_text="Passo de volume",
            help_text="Valor usado ao aumentar ou diminuir o volume com as setas para cima e para baixo.",
            min_value=1,
            max_value=25,
        )
        crossfade_group, self.crossfade_ctrl = self._build_spin_control_group(
            page,
            label_text="Crossfade (segundos, 0 desativa)",
            help_text=(
                "Define por quantos segundos duas faixas de áudio se sobrepõem na transição. "
                "Use 0 para desativar. O crossfade só é aplicado entre arquivos de áudio."
            ),
            min_value=0,
            max_value=MAX_CROSSFADE_SECONDS,
        )
        seek_step_group, self.seek_step_ctrl = self._build_spin_control_group(
            page,
            label_text="Passo de busca (segundos)",
            help_text="Valor usado para avançar ou retroceder na mídia com as setas esquerda e direita.",
            min_value=1,
            max_value=120,
        )
        repeat_group, self.repeat_mode_choice = self._build_choice_control_group(
            page,
            label_text="Repetição padrão",
            help_text="Modo de repetição aplicado automaticamente às playlists novas.",
            choices=[REPEAT_MODE_LABELS[mode] for mode in REPEAT_MODES],
        )

        for group in (volume_group, volume_step_group, crossfade_group, seek_step_group, repeat_group):
            playback_box.Add(group, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 6)

        playback_box.Add(self.shuffle_new_playlists_checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)

        page_sizer.Add(info_label, 0, wx.ALL | wx.EXPAND, 10)
        page_sizer.Add(playback_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        self.notebook.AddPage(page, "Reprodução")

    def _build_accessibility_tab(self):
        page, page_sizer = self._create_tab_page("Acessibilidade")

        info_label = wx.StaticText(
            page,
            label="Configurações ligadas aos anúncios enviados ao leitor de tela e à navegação das preferências.",
        )
        info_label.Wrap(520)

        accessibility_box = wx.StaticBoxSizer(wx.StaticBox(page, label="Leitor de tela"), wx.VERTICAL)
        self.announcements_enabled_checkbox = wx.CheckBox(page, label="Ativar a&núncios de acessibilidade")
        self._configure_checkbox(
            self.announcements_enabled_checkbox,
            "Ativar anúncios de acessibilidade",
            "Liga ou desliga os anúncios enviados ao leitor de tela.",
        )
        accessibility_box.Add(self.announcements_enabled_checkbox, 0, wx.ALL | wx.EXPAND, 6)

        help_label = wx.StaticText(
            page,
            label="Se essa opção estiver desligada, o player deixa de anunciar mudanças como tempo, volume e troca de abas.",
        )
        help_label.Wrap(520)

        page_sizer.Add(info_label, 0, wx.ALL | wx.EXPAND, 10)
        page_sizer.Add(accessibility_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        page_sizer.Add(help_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        self.notebook.AddPage(page, "Acessibilidade")

    def _create_tab_page(self, name):
        page = wx.Panel(self.notebook)
        page.SetName(name)
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        page.SetSizer(page_sizer)
        return page, page_sizer

    def _configure_checkbox(self, checkbox, name, help_text):
        checkbox.SetName(name)
        checkbox.SetToolTip(help_text)
        checkbox.SetHelpText(help_text)

    def _configure_control(self, control, name, help_text):
        control.SetName(name)
        control.SetToolTip(help_text)
        control.SetHelpText(help_text)

    def _build_spin_control_group(self, parent, label_text, help_text, min_value, max_value):
        label = wx.StaticText(parent, label=f"{label_text}:")
        control = wx.SpinCtrl(parent, min=min_value, max=max_value, name=label_text)
        self._configure_control(control, label_text, help_text)
        return self._build_labeled_control_group(parent, label_text, label, control, help_text), control

    def _build_choice_control_group(self, parent, label_text, help_text, choices):
        label = wx.StaticText(parent, label=f"{label_text}:")
        control = wx.Choice(parent, choices=choices, name=label_text)
        self._configure_control(control, label_text, help_text)
        return self._build_labeled_control_group(parent, label_text, label, control, help_text), control

    def _build_labeled_control_group(self, parent, label_text, visible_label, control, help_text):
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(parent, label=label_text), wx.VERTICAL)
        help_label = wx.StaticText(parent, label=help_text)
        visible_label.Wrap(500)
        help_label.Wrap(500)

        box_sizer.Add(visible_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 6)
        box_sizer.Add(control, 0, wx.ALL | wx.EXPAND, 6)
        box_sizer.Add(help_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
        return box_sizer

    def _populate_controls(self, settings):
        self.restore_session_checkbox.SetValue(settings.restore_session_on_startup)
        self.remember_window_size_checkbox.SetValue(settings.remember_window_size)
        self.remember_last_folder_checkbox.SetValue(settings.remember_last_folder)
        self.confirm_on_exit_checkbox.SetValue(settings.confirm_on_exit)
        self.announcements_enabled_checkbox.SetValue(settings.announcements_enabled)
        self.default_volume_ctrl.SetValue(settings.default_volume)
        self.crossfade_ctrl.SetValue(settings.crossfade_seconds)
        self.volume_step_ctrl.SetValue(settings.volume_step)
        self.seek_step_ctrl.SetValue(settings.seek_step_seconds)
        self.shuffle_new_playlists_checkbox.SetValue(settings.shuffle_new_playlists)

        repeat_mode_index = REPEAT_MODES.index(settings.repeat_mode_new_playlists)
        self.repeat_mode_choice.SetSelection(repeat_mode_index)

    def get_settings(self):
        settings = replace(self._settings)
        settings.restore_session_on_startup = self.restore_session_checkbox.GetValue()
        settings.remember_window_size = self.remember_window_size_checkbox.GetValue()
        settings.remember_last_folder = self.remember_last_folder_checkbox.GetValue()
        settings.confirm_on_exit = self.confirm_on_exit_checkbox.GetValue()
        settings.announcements_enabled = self.announcements_enabled_checkbox.GetValue()
        settings.default_volume = int(self.default_volume_ctrl.GetValue())
        settings.crossfade_seconds = int(self.crossfade_ctrl.GetValue())
        settings.volume_step = int(self.volume_step_ctrl.GetValue())
        settings.seek_step_seconds = int(self.seek_step_ctrl.GetValue())
        settings.shuffle_new_playlists = self.shuffle_new_playlists_checkbox.GetValue()
        settings.repeat_mode_new_playlists = REPEAT_MODES[self.repeat_mode_choice.GetSelection()]

        if not settings.remember_last_folder:
            settings.last_open_dir = ""

        return settings

    def on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            if self.IsModal():
                self.EndModal(wx.ID_CANCEL)
            else:
                self.Close()
            return

        event.Skip()
