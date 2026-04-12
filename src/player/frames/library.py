from .library_loader import FrameLibraryLoaderMixin
from .library_navigation import FrameLibraryNavigationMixin
from .library_tabs import FrameLibraryTabsMixin


class FrameLibraryMixin(
    FrameLibraryLoaderMixin,
    FrameLibraryNavigationMixin,
    FrameLibraryTabsMixin,
):
    pass
