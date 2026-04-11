import wx

from .frame import VLCPlayerFrame


def main():
    app = wx.App(False)
    VLCPlayerFrame()
    app.MainLoop()
