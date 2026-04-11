import wx

from .equalizer import format_frequency_label


class EqualizerTabPanel(wx.Panel):
    def __init__(
        self,
        parent,
        *,
        on_toggle_enabled,
        on_select_preset,
        on_create_preset,
        on_edit_preset,
        on_duplicate_preset,
        on_delete_preset,
    ):
        super().__init__(parent)

        self._choice_preset_ids = []
        self._updating_controls = False
        self._on_toggle_enabled = on_toggle_enabled
        self._on_select_preset = on_select_preset
        self._on_create_preset = on_create_preset
        self._on_edit_preset = on_edit_preset
        self._on_duplicate_preset = on_duplicate_preset
        self._on_delete_preset = on_delete_preset
        self._band_value_labels = []

        root_sizer = wx.BoxSizer(wx.VERTICAL)

        intro_label = wx.StaticText(
            self,
            label=(
                "Ajuste o equalizador da aba de mídia ativa. "
                "Use os botões para criar, editar, duplicar ou excluir presets personalizados."
            ),
        )
        intro_label.Wrap(620)
        root_sizer.Add(intro_label, 0, wx.ALL | wx.EXPAND, 10)

        context_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Contexto"), wx.VERTICAL)
        self.target_tab_label = wx.StaticText(self, label="Aba alvo: nenhuma")
        self.preset_description_label = wx.StaticText(self, label="")
        self.preset_description_label.Wrap(600)
        context_box.Add(self.target_tab_label, 0, wx.ALL | wx.EXPAND, 6)
        context_box.Add(self.preset_description_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)
        root_sizer.Add(context_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        controls_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Preset ativo"), wx.VERTICAL)
        self.enable_checkbox = wx.CheckBox(self, label="Ativar equalizador nesta aba")
        self.enable_checkbox.SetName("Ativar equalizador nesta aba")
        self.enable_checkbox.SetHelpText("Liga ou desliga o equalizador apenas para a aba de mídia ativa.")
        self.enable_checkbox.SetToolTip("Liga ou desliga o equalizador apenas para a aba de mídia ativa.")

        preset_label = wx.StaticText(self, label="Preset:")
        self.preset_choice = wx.Choice(self)
        self.preset_choice.SetName("Preset do equalizador")
        self.preset_choice.SetHelpText("Escolha o preset que será usado na aba de mídia ativa.")
        self.preset_choice.SetToolTip("Escolha o preset que será usado na aba de mídia ativa.")

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.new_button = wx.Button(self, label="Novo...")
        self.edit_button = wx.Button(self, label="Editar...")
        self.duplicate_button = wx.Button(self, label="Duplicar...")
        self.delete_button = wx.Button(self, label="Excluir")

        for button in (self.new_button, self.edit_button, self.duplicate_button, self.delete_button):
            button_sizer.Add(button, 0, wx.RIGHT, 8)

        controls_box.Add(self.enable_checkbox, 0, wx.ALL | wx.EXPAND, 6)
        controls_box.Add(preset_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 6)
        controls_box.Add(self.preset_choice, 0, wx.ALL | wx.EXPAND, 6)
        controls_box.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 6)
        root_sizer.Add(controls_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        values_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Resumo do preset"), wx.VERTICAL)
        values_help = wx.StaticText(
            self,
            label="Os valores abaixo mostram a curva do preset atualmente selecionado.",
        )
        values_help.Wrap(600)
        values_box.Add(values_help, 0, wx.ALL | wx.EXPAND, 6)

        values_grid = wx.FlexGridSizer(cols=2, hgap=10, vgap=8)
        values_grid.AddGrowableCol(1, 1)
        values_grid.Add(wx.StaticText(self, label="Pré-amplificação:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.preamp_value_label = wx.StaticText(self, label="0.0 dB")
        values_grid.Add(self.preamp_value_label, 0, wx.ALIGN_CENTER_VERTICAL)
        values_box.Add(values_grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)

        self._values_grid = values_grid
        root_sizer.Add(values_box, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        self.SetSizer(root_sizer)

        self.enable_checkbox.Bind(wx.EVT_CHECKBOX, self.on_toggle_enabled)
        self.preset_choice.Bind(wx.EVT_CHOICE, self.on_select_preset)
        self.new_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_create_preset())
        self.edit_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_edit_preset())
        self.duplicate_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_duplicate_preset())
        self.delete_button.Bind(wx.EVT_BUTTON, lambda _event: self._on_delete_preset())

    def update_view(self, *, target_tab_title, equalizer_enabled, presets, selected_preset_id, selected_preset, band_frequencies_hz):
        self._updating_controls = True
        try:
            self.target_tab_label.SetLabel(f"Aba alvo: {target_tab_title}")
            self.enable_checkbox.SetValue(bool(equalizer_enabled))

            self.preset_choice.Clear()
            self._choice_preset_ids = []
            for preset in presets:
                suffix = " (VLC)" if preset.is_builtin else ""
                self.preset_choice.Append(f"{preset.name}{suffix}")
                self._choice_preset_ids.append(preset.preset_id)

            selection_index = 0
            if selected_preset_id in self._choice_preset_ids:
                selection_index = self._choice_preset_ids.index(selected_preset_id)
            elif selected_preset and selected_preset.preset_id in self._choice_preset_ids:
                selection_index = self._choice_preset_ids.index(selected_preset.preset_id)

            if self._choice_preset_ids:
                self.preset_choice.SetSelection(selection_index)

            self._refresh_value_rows(band_frequencies_hz)
            self.preset_description_label.SetLabel(selected_preset.description if selected_preset else "")
            self.preamp_value_label.SetLabel(
                f"{selected_preset.preamp_db:+.1f} dB" if selected_preset else "0.0 dB"
            )

            selected_band_gains = list(selected_preset.band_gains_db) if selected_preset else []
            for label, gain_db in zip(self._band_value_labels, selected_band_gains):
                label.SetLabel(f"{gain_db:+.1f} dB")

            if len(selected_band_gains) < len(self._band_value_labels):
                for label in self._band_value_labels[len(selected_band_gains):]:
                    label.SetLabel("0.0 dB")

            has_selection = selected_preset is not None
            self.edit_button.Enable(has_selection)
            self.duplicate_button.Enable(has_selection)
            self.delete_button.Enable(bool(has_selection and not selected_preset.is_builtin))
            self.Layout()
        finally:
            self._updating_controls = False

    def _refresh_value_rows(self, band_frequencies_hz):
        while len(self._band_value_labels) < len(band_frequencies_hz):
            frequency_index = len(self._band_value_labels)
            frequency_label = wx.StaticText(self, label=f"{format_frequency_label(band_frequencies_hz[frequency_index])}:")
            value_label = wx.StaticText(self, label="0.0 dB")
            self._values_grid.Add(frequency_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self._values_grid.Add(value_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self._band_value_labels.append(value_label)

    def on_toggle_enabled(self, event):
        if self._updating_controls:
            event.Skip()
            return

        self._on_toggle_enabled(self.enable_checkbox.GetValue())

    def on_select_preset(self, event):
        if self._updating_controls:
            event.Skip()
            return

        selection = self.preset_choice.GetSelection()
        if not 0 <= selection < len(self._choice_preset_ids):
            return

        self._on_select_preset(self._choice_preset_ids[selection])
