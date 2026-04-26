import json
import os

from ..session import get_app_storage_dir
from .models import AppSettings


SETTINGS_FILE_NAME = "settings.json"


def load_settings():
    settings_path = os.path.join(_get_storage_dir(), SETTINGS_FILE_NAME)
    if not os.path.exists(settings_path):
        return AppSettings()

    try:
        with open(settings_path, "r", encoding="utf-8") as settings_file:
            payload = json.load(settings_file)
    except (json.JSONDecodeError, OSError):
        return AppSettings()

    if not isinstance(payload, dict):
        return AppSettings()

    return AppSettings.from_dict(payload)


def save_settings(settings):
    settings_path = os.path.join(_get_storage_dir(), SETTINGS_FILE_NAME)
    with open(settings_path, "w", encoding="utf-8") as settings_file:
        json.dump(settings.to_dict(), settings_file, ensure_ascii=False, indent=2)


def _get_storage_dir():
    return get_app_storage_dir()
