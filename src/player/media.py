import os
from dataclasses import dataclass

from .constants import SUPPORTED_MEDIA_EXTENSIONS


FOLDER_ENTRY_PARENT = "parent"
FOLDER_ENTRY_DIRECTORY = "directory"
FOLDER_ENTRY_FILE = "file"


@dataclass(frozen=True)
class FolderBrowserEntry:
    path: str
    label: str
    entry_type: str

    @property
    def is_parent(self):
        return self.entry_type == FOLDER_ENTRY_PARENT

    @property
    def is_directory(self):
        return self.entry_type in {FOLDER_ENTRY_PARENT, FOLDER_ENTRY_DIRECTORY}

    @property
    def is_file(self):
        return self.entry_type == FOLDER_ENTRY_FILE


def is_supported_media(filename):
    return os.path.splitext(filename)[1].lower() in SUPPORTED_MEDIA_EXTENSIONS


def folder_display_name(folder_path):
    normalized_path = os.path.abspath(os.path.normpath(str(folder_path or "")))
    if not normalized_path:
        return "Pasta"

    folder_name = os.path.basename(normalized_path.rstrip("\\/"))
    return folder_name or normalized_path


def discover_media_files(folder_path):
    files = []
    for item in sorted(os.listdir(folder_path), key=str.lower):
        full_path = os.path.join(folder_path, item)
        if os.path.isfile(full_path) and is_supported_media(item):
            files.append(full_path)
    return files


def discover_folder_entries(folder_path):
    normalized_folder_path = os.path.abspath(os.path.normpath(folder_path))
    entries = []

    parent_path = os.path.dirname(normalized_folder_path)
    if parent_path and parent_path != normalized_folder_path:
        entries.append(
            FolderBrowserEntry(
                path=parent_path,
                label="[..] Pasta acima",
                entry_type=FOLDER_ENTRY_PARENT,
            )
        )

    directories = []
    files = []
    for item in sorted(os.listdir(normalized_folder_path), key=str.lower):
        full_path = os.path.join(normalized_folder_path, item)
        if os.path.isdir(full_path):
            directories.append(
                FolderBrowserEntry(
                    path=full_path,
                    label=item,
                    entry_type=FOLDER_ENTRY_DIRECTORY,
                )
            )
            continue

        if os.path.isfile(full_path) and is_supported_media(item):
            files.append(
                FolderBrowserEntry(
                    path=full_path,
                    label=item,
                    entry_type=FOLDER_ENTRY_FILE,
                )
            )

    entries.extend(directories)
    entries.extend(files)
    return entries
