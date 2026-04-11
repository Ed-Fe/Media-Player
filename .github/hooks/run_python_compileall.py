from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

WRITE_TOOL_TOKENS = {
    "apply_patch",
    "create_file",
    "vscode_renameSymbol",
    "mcp_github_create_or_update_file",
    "mcp_io_github_git_create_or_update_file",
    "mcp_github_push_files",
}

PYTHON_FILE_PATTERN = re.compile(r"(?i)(^|[\\/])[^\\/\n]+\.pyw?\b")


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from iter_strings(item)
        return

    if isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def should_run_compileall(raw_input: str) -> bool:
    if not raw_input.strip():
        return False

    texts = [raw_input]
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        texts.extend(iter_strings(payload))

    joined_text = "\n".join(texts)
    has_write_tool = any(token in joined_text for token in WRITE_TOOL_TOKENS)
    touches_python_file = PYTHON_FILE_PATTERN.search(joined_text) is not None
    return has_write_tool and touches_python_file


def pick_python_executable(workspace_root: Path) -> str:
    candidates = []
    if sys.platform.startswith("win"):
        candidates.append(workspace_root / ".venv" / "Scripts" / "python.exe")
    else:
        candidates.append(workspace_root / ".venv" / "bin" / "python")

    candidates.append(Path(sys.executable))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return sys.executable


def print_result(message: str) -> None:
    print(json.dumps({"continue": True, "systemMessage": message}))


def main() -> int:
    raw_input = sys.stdin.read()
    if not should_run_compileall(raw_input):
        return 0

    workspace_root = Path(__file__).resolve().parents[2]
    python_executable = pick_python_executable(workspace_root)
    result = subprocess.run(
        [python_executable, "-m", "compileall", "src"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode == 0:
        print_result("Validação automática: python -m compileall src executado com sucesso.")
        return 0

    if result.stdout:
        sys.stderr.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    print_result("Validação automática falhou: revise a saída de python -m compileall src.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
