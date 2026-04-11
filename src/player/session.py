import json
import os


SESSION_FILE_NAME = "session.json"
APP_STORAGE_DIR = "MediaPlayerWxVLC"


def _get_storage_dir():
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")

    storage_dir = os.path.join(base_dir, APP_STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def load_session():
    session_path = os.path.join(_get_storage_dir(), SESSION_FILE_NAME)
    if not os.path.exists(session_path):
        return None

    try:
        with open(session_path, "r", encoding="utf-8") as session_file:
            return json.load(session_file)
    except (json.JSONDecodeError, OSError):
        return None


def save_session(payload):
    session_path = os.path.join(_get_storage_dir(), SESSION_FILE_NAME)
    with open(session_path, "w", encoding="utf-8") as session_file:
        json.dump(payload, session_file, ensure_ascii=False, indent=2)
