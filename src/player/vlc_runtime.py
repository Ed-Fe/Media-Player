from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_runtime_dirs() -> list[Path]:
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "vlc")

    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "vlc")
    candidates.append(Path.cwd() / "vlc")

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def _is_valid_runtime_dir(directory: Path) -> bool:
    return (directory / "libvlc.dll").is_file() and (directory / "plugins").is_dir()


def bootstrap_vlc_runtime() -> bool:
    if not sys.platform.startswith("win"):
        return False

    for runtime_dir in _candidate_runtime_dirs():
        if not _is_valid_runtime_dir(runtime_dir):
            continue

        plugins_dir = runtime_dir / "plugins"
        os.environ.setdefault("VLC_PLUGIN_PATH", str(plugins_dir))
        os.environ["PATH"] = f"{runtime_dir}{os.pathsep}{os.environ.get('PATH', '')}"

        add_dll_directory = getattr(os, "add_dll_directory", None)
        if add_dll_directory is not None:
            add_dll_directory(str(runtime_dir))
        return True

    return False