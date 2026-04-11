import os


REMOTE_PREFIXES = (
    "http://",
    "https://",
    "rtsp://",
    "mms://",
    "ftp://",
    "file://",
)


def is_remote_media_path(path):
    normalized = str(path).strip().lower()
    return normalized.startswith(REMOTE_PREFIXES)


def playlist_display_name(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]


def _resolve_playlist_entry(base_dir, entry):
    if is_remote_media_path(entry):
        return entry

    normalized_entry = os.path.expandvars(entry)
    if not os.path.isabs(normalized_entry):
        normalized_entry = os.path.normpath(os.path.join(base_dir, normalized_entry))
    else:
        normalized_entry = os.path.normpath(normalized_entry)

    if os.path.exists(normalized_entry):
        return normalized_entry
    return None


def load_playlist(file_path):
    base_dir = os.path.dirname(file_path)
    candidates = []

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as playlist_file:
                candidates = playlist_file.readlines()
            break
        except UnicodeDecodeError:
            continue

    items = []
    for raw_line in candidates:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        resolved = _resolve_playlist_entry(base_dir, line)
        if resolved:
            items.append(resolved)

    return items


def save_playlist(file_path, items):
    base_dir = os.path.dirname(file_path)
    lines = ["#EXTM3U"]

    for item in items:
        if is_remote_media_path(item):
            lines.append(item)
            continue

        normalized_item = os.path.abspath(item)
        try:
            stored_entry = os.path.relpath(normalized_item, base_dir)
        except ValueError:
            stored_entry = normalized_item

        lines.append(stored_entry)

    with open(file_path, "w", encoding="utf-8") as playlist_file:
        playlist_file.write("\n".join(lines) + "\n")
