from __future__ import annotations

import argparse
import ctypes
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path


LOG_DIRECTORY = Path(tempfile.gettempdir()) / "MediaPlayerUpdater"
LOG_FILE_PATH = LOG_DIRECTORY / "updater.log"
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
SYNCHRONIZE = 0x00100000


def main() -> int:
    args = parse_args()
    log_message("Iniciando atualizador externo.")
    log_message(f"Pasta do aplicativo: {args.app_dir}")
    log_message(f"Pacote recebido: {args.package}")

    try:
        run_update(args)
    except Exception as exc:
        log_message(f"Falha durante a atualização: {exc}")
        show_error_message(
            "Não foi possível concluir a atualização automática. "
            f"Consulte o log em: {LOG_FILE_PATH}"
        )
        return 1

    log_message("Atualização concluída com sucesso.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Aplica uma atualização do Media Player a partir de um arquivo ZIP.")
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--restart-executable", required=True)
    return parser.parse_args()


def run_update(args):
    app_dir = Path(args.app_dir).resolve()
    package_path = Path(args.package).resolve()
    restart_executable = str(args.restart_executable).strip()
    if not app_dir.exists() or not app_dir.is_dir():
        raise FileNotFoundError(f"Pasta do aplicativo não encontrada: {app_dir}")
    if not package_path.exists() or not package_path.is_file():
        raise FileNotFoundError(f"Pacote de atualização não encontrado: {package_path}")

    log_message("Aguardando o encerramento do processo principal.")
    wait_for_process_exit(args.parent_pid, timeout_seconds=120)

    working_directory = Path(tempfile.mkdtemp(prefix="mediaplayer-updater-job-"))
    extract_directory = working_directory / "extract"
    backup_directory = working_directory / "backup"

    log_message(f"Extraindo atualização em: {extract_directory}")
    extract_release_archive(package_path, extract_directory)
    payload_root = locate_payload_root(extract_directory)

    log_message(f"Criando backup da instalação atual em: {backup_directory}")
    backup_installation(app_dir, backup_directory)

    try:
        log_message("Copiando nova versão para a pasta do aplicativo.")
        replace_installation(app_dir, payload_root)
    except Exception:
        log_message("Falha ao copiar a nova versão. Restaurando backup.")
        restore_installation(app_dir, backup_directory)
        raise

    restart_path = app_dir / restart_executable
    log_message(f"Reiniciando aplicativo por: {restart_path}")
    restart_application(restart_path)


def wait_for_process_exit(process_id: int, *, timeout_seconds: int):
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(process_id))
    if not process_handle:
        log_message("Processo principal já havia encerrado.")
        return

    try:
        wait_result = kernel32.WaitForSingleObject(process_handle, timeout_seconds * 1000)
        if wait_result == WAIT_OBJECT_0:
            return
        if wait_result == WAIT_TIMEOUT:
            raise TimeoutError("Tempo esgotado aguardando o encerramento do aplicativo.")
        if wait_result == WAIT_FAILED:
            raise OSError("Falha ao aguardar o encerramento do processo principal.")
        raise OSError(f"Resultado inesperado ao aguardar o processo principal: {wait_result}")
    finally:
        kernel32.CloseHandle(process_handle)


def extract_release_archive(package_path: Path, extract_directory: Path):
    extract_directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path) as archive_file:
        safe_extract_all(archive_file, extract_directory)


def safe_extract_all(archive_file: zipfile.ZipFile, extract_directory: Path):
    target_root = extract_directory.resolve()
    for member in archive_file.infolist():
        target_path = (extract_directory / member.filename).resolve()
        try:
            target_path.relative_to(target_root)
        except ValueError as exc:
            raise ValueError("O pacote de atualização contém caminhos inválidos.")
        except Exception as exc:
            raise ValueError("Não foi possível validar os caminhos do pacote de atualização.") from exc
    archive_file.extractall(extract_directory)


def locate_payload_root(extract_directory: Path) -> Path:
    entries = [entry for entry in extract_directory.iterdir() if entry.name not in {"__MACOSX"}]
    if not entries:
        raise ValueError("O pacote de atualização foi extraído, mas não contém arquivos válidos.")
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extract_directory


def backup_installation(source_directory: Path, backup_directory: Path):
    if backup_directory.exists():
        shutil.rmtree(backup_directory, ignore_errors=True)
    backup_directory.mkdir(parents=True, exist_ok=True)
    copy_directory_contents(source_directory, backup_directory)


def replace_installation(target_directory: Path, payload_root: Path):
    clear_directory(target_directory)
    copy_directory_contents(payload_root, target_directory)


def restore_installation(target_directory: Path, backup_directory: Path):
    clear_directory(target_directory)
    copy_directory_contents(backup_directory, target_directory)


def clear_directory(directory: Path):
    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=False)
        else:
            child.unlink(missing_ok=True)


def copy_directory_contents(source_directory: Path, target_directory: Path):
    target_directory.mkdir(parents=True, exist_ok=True)
    for child in source_directory.iterdir():
        destination = target_directory / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(child, destination)


def restart_application(executable_path: Path):
    if not executable_path.exists():
        raise FileNotFoundError(f"Executável principal não encontrado após a atualização: {executable_path}")

    creation_flags = 0
    creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        [str(executable_path)],
        cwd=str(executable_path.parent),
        close_fds=True,
        creationflags=creation_flags,
    )


def log_message(message: str):
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def show_error_message(message: str):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "Atualização do Media Player", 0x10)
    except Exception:
        print(message, file=sys.stderr)
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
