import wx

from .frame import VLCPlayerFrame


def main():
    app = wx.App(False)
    frame = VLCPlayerFrame()
    app.SetTopWindow(frame)
    app.MainLoop()
