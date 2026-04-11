import queue
import threading
from importlib import import_module

import wx

try:
    accessible_output2_auto = import_module("accessible_output2.outputs.auto")
    AutoOutput = getattr(accessible_output2_auto, "Auto", None)
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency is missing
    AutoOutput = None
except Exception:  # pragma: no cover - defensive guard for optional dependency
    AutoOutput = None


class NamedControlAccessible(wx.Accessible):
    def __init__(self, window, name, description="", role=None, value_provider=None):
        super().__init__(window)
        self._window = window
        self._name = name
        self._description = description
        self._role = role
        self._value_provider = value_provider

    def GetName(self, childId):
        if childId != 0:
            return wx.ACC_NOT_IMPLEMENTED, ""
        return wx.ACC_OK, self._name

    def GetDescription(self, childId):
        if childId != 0:
            return wx.ACC_NOT_IMPLEMENTED, ""
        return wx.ACC_OK, self._description

    def GetHelpText(self, childId):
        if childId != 0:
            return wx.ACC_NOT_IMPLEMENTED, ""
        return wx.ACC_OK, self._description

    def GetRole(self, childId):
        if childId != 0 or self._role is None:
            return wx.ACC_NOT_IMPLEMENTED, 0
        return wx.ACC_OK, self._role

    def GetValue(self, childId):
        if childId != 0 or self._value_provider is None:
            return wx.ACC_NOT_IMPLEMENTED, ""

        try:
            value = self._value_provider()
        except Exception:
            return wx.ACC_NOT_IMPLEMENTED, ""

        return wx.ACC_OK, str(value)


def attach_named_accessible(window, name, description="", role=None, value_provider=None):
    if not hasattr(wx, "Accessible") or not hasattr(window, "SetAccessible"):
        return None

    accessible = NamedControlAccessible(
        window=window,
        name=name,
        description=description,
        role=role,
        value_provider=value_provider,
    )
    window.SetAccessible(accessible)
    return accessible


class ScreenReaderAnnouncer:
    def __init__(self, prefer_screen_reader_only=True):
        self._enabled = AutoOutput is not None
        self._prefer_screen_reader_only = prefer_screen_reader_only
        self._queue = queue.Queue()
        self._stop_token = object()
        self._worker_thread = None
        self._output = None

        if self._enabled:
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def speak(self, message):
        if not self._enabled or not message:
            return

        self._queue.put(message)

    def close(self):
        if not self._enabled:
            return

        self._queue.put(self._stop_token)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def _worker(self):
        if AutoOutput is None:
            return

        try:
            self._output = AutoOutput()
        except Exception:
            self._output = None
            return

        while True:
            message = self._queue.get()
            if message is self._stop_token:
                break

            try:
                self._speak_message(message)
            except Exception:
                continue

    def _speak_message(self, message):
        if not self._output:
            return

        if self._prefer_screen_reader_only and hasattr(self._output, "is_system_output"):
            try:
                if self._output.is_system_output():
                    return
            except Exception:
                pass

        try:
            self._output.speak(message, interrupt=True)
            return
        except TypeError:
            pass
        except Exception:
            pass

        try:
            self._output.speak(message)
            return
        except Exception:
            pass

        try:
            self._output.output(message)
        except Exception:
            return
