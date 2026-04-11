import os

import wx


class PlaylistBrowserPanel(wx.Panel):
    def __init__(
        self,
        parent,
        on_activate_item,
        on_remove_item,
        on_preview_item=None,
        on_go_back=None,
        on_toggle_navigation_mode=None,
    ):
        super().__init__(parent)

        self._on_activate_item = on_activate_item
        self._on_remove_item = on_remove_item
        self._on_preview_item = on_preview_item
        self._on_go_back = on_go_back
        self._on_toggle_navigation_mode = on_toggle_navigation_mode
        self._items = []
        self._mode = "playlist"
        self._suppress_selection_event = False

        root_sizer = wx.BoxSizer(wx.VERTICAL)

        self.header_label = wx.StaticText(self, label="Playlist")
        self.items_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.hint_label = wx.StaticText(
            self,
            label="Enter toca o item selecionado. Delete remove. F6 volta ao player.",
        )
        self.hint_label.Wrap(260)

        root_sizer.Add(self.header_label, 0, wx.ALL | wx.EXPAND, 10)
        root_sizer.Add(self.items_list, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        root_sizer.Add(self.hint_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)

        self.SetSizer(root_sizer)
        self.SetMinSize((300, 320))

        self.items_list.Bind(wx.EVT_LISTBOX, self.on_selection_changed)
        self.items_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_activate)
        self.items_list.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

    def update_playlist(self, playlist_state):
        self._mode = "playlist"
        self._items = list(playlist_state.items)
        self._suppress_selection_event = True

        if playlist_state.items:
            labels = [
                self._format_label(index, item, playlist_state.current_index)
                for index, item in enumerate(playlist_state.items)
            ]
            selection = playlist_state.current_index if 0 <= playlist_state.current_index < len(labels) else wx.NOT_FOUND
            self._update_list_items(labels, selection, preserve_focused_labels=True)
        else:
            self._update_list_items(
                ["Nenhum item nesta playlist."],
                wx.NOT_FOUND,
                preserve_focused_labels=True,
            )

        self.header_label.SetLabel(
            f"{playlist_state.title} — {len(playlist_state.items)} item(ns)"
        )
        self.hint_label.SetLabel(
            "Enter toca o item selecionado. Delete remove. F6 volta ao player."
        )
        self._suppress_selection_event = False

    def update_folder(self, title, current_path, entries, selected_path, current_media_path):
        self._mode = "folder"
        self._items = list(entries)
        self._suppress_selection_event = True

        if entries:
            labels = [self._format_folder_label(entry, current_media_path) for entry in entries]
            selection = self._find_selection(entries, selected_path, current_media_path)
            self._update_list_items(labels, selection, preserve_focused_labels=True)
        else:
            self._update_list_items(
                ["Nenhuma pasta ou mídia nesta localização."],
                wx.NOT_FOUND,
                preserve_focused_labels=True,
            )

        self.header_label.SetLabel(f"{title} — {current_path}")
        self.hint_label.SetLabel(
            "Enter entra na pasta ou toca o arquivo. Backspace volta. F6 volta ao player."
        )
        self.hint_label.Wrap(260)
        self._suppress_selection_event = False

    def focus_current_item(self):
        self.items_list.SetFocus()

    def is_item_navigation_active(self):
        focused_window = self.FindFocus()
        return self.IsShown() and focused_window is not None and focused_window is self.items_list

    def _format_label(self, index, item, current_index):
        prefix = "▶ " if index == current_index else "   "
        return f"{prefix}{index + 1}. {os.path.basename(item) or item}"

    def _format_folder_label(self, entry, current_media_path):
        if getattr(entry, "is_parent", False):
            return entry.label

        if getattr(entry, "is_directory", False):
            return entry.label

        prefix = "▶ " if getattr(entry, "path", None) == current_media_path else "   "
        return f"{prefix}{entry.label}"

    def _find_selection(self, entries, selected_path, current_media_path):
        target_path = selected_path or current_media_path
        if target_path:
            normalized_target = os.path.normcase(os.path.normpath(target_path))
            for index, entry in enumerate(entries):
                entry_path = getattr(entry, "path", None)
                if not entry_path:
                    continue
                if os.path.normcase(os.path.normpath(entry_path)) == normalized_target:
                    return index

        for index, entry in enumerate(entries):
            if not getattr(entry, "is_parent", False):
                return index

        return 0 if entries else wx.NOT_FOUND

    def _strip_state_prefix(self, label):
        if label.startswith("▶ "):
            return label[2:]
        if label.startswith("   "):
            return label[3:]
        return label

    def _update_list_items(self, labels, selection, preserve_focused_labels=False):
        current_labels = [self.items_list.GetString(index) for index in range(self.items_list.GetCount())]
        focused_navigation = preserve_focused_labels and self.is_item_navigation_active()
        current_base_labels = [self._strip_state_prefix(label) for label in current_labels]
        target_base_labels = [self._strip_state_prefix(label) for label in labels]
        labels_need_rebuild = current_base_labels != target_base_labels
        labels_need_redraw = current_labels != labels

        if labels_need_rebuild or (labels_need_redraw and not focused_navigation):
            if len(current_labels) == len(labels):
                for index, label in enumerate(labels):
                    if current_labels[index] != label:
                        self.items_list.SetString(index, label)
            else:
                self.items_list.Set(labels)

        current_selection = self.items_list.GetSelection()
        if selection == wx.NOT_FOUND:
            if current_selection != wx.NOT_FOUND:
                self.items_list.SetSelection(wx.NOT_FOUND)
            return

        if current_selection != selection:
            self.items_list.SetSelection(selection)

    def _activate_selected(self):
        selection = self.items_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self._items):
            return
        self._on_activate_item(selection)

    def _remove_selected(self):
        selection = self.items_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self._items):
            return
        self._on_remove_item(selection)

    def on_activate(self, _event):
        self._activate_selected()

    def on_selection_changed(self, _event):
        if self._mode != "folder" or self._suppress_selection_event:
            return

        selection = self.items_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self._items):
            return

        entry = self._items[selection]
        if not getattr(entry, "is_file", False) or not self._on_preview_item:
            return

        self._on_preview_item(selection)

    def on_key_down(self, event):
        key_code = event.GetKeyCode()

        if key_code == wx.WXK_F6:
            if self._on_toggle_navigation_mode:
                self._on_toggle_navigation_mode()
            return

        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._activate_selected()
            return

        if self._mode == "folder" and key_code == wx.WXK_BACK:
            if self._on_go_back:
                self._on_go_back()
            return

        if self._mode == "playlist" and key_code in (wx.WXK_DELETE, wx.WXK_BACK):
            self._remove_selected()
            return

        if key_code == wx.WXK_ESCAPE:
            if self._on_toggle_navigation_mode:
                self._on_toggle_navigation_mode()
            return

        event.DoAllowNextEvent()
