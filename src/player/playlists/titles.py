import os


def default_playlist_title(number):
    return f"Playlist {number}"


def build_playlist_title(items, explicit_title=None):
    if explicit_title:
        return explicit_title

    normalized_items = list(items)
    if not normalized_items:
        return default_playlist_title(1)

    if len(normalized_items) == 1:
        return os.path.splitext(os.path.basename(normalized_items[0]))[0]

    parent_directories = {os.path.dirname(path) for path in normalized_items}
    if len(parent_directories) == 1:
        folder_name = os.path.basename(parent_directories.pop())
        if folder_name:
            return f"{folder_name} ({len(normalized_items)})"

    return f"Seleção ({len(normalized_items)})"


def build_folder_tab_title(folder_path):
    normalized_path = os.path.abspath(os.path.normpath(str(folder_path or "")))
    folder_name = os.path.basename(normalized_path.rstrip("\\/")) or normalized_path
    return f"Pasta: {folder_name}"
