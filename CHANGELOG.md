# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 

## [0.2.0] - 2026-04-11

### Added
- Verificação automática de atualizações ao iniciar a versão empacotada do Windows.
- Visualização das notas da release antes de confirmar o download da atualização.
- Diálogo de download com barra de progresso para baixar novas releases antes de instalar.
- Atualizador externo para aplicar o ZIP da release sem sobrescrever arquivos em uso.
- Geração e publicação do arquivo `MediaPlayer-windows.zip.sha256` nas releases.
- Script local para gerar a release Windows e roteiro documentado para testar o atualizador ponta a ponta.

### Changed
- Workflow de release do Windows para incluir `MediaPlayerUpdater.exe` no pacote publicado.

### Fixed
- 

## [0.1.0] - 2026-04-11

### Added
- Windows release workflow (`.github/workflows/release-windows.yml`) to build and publish a ZIP package.
- Bundled VLC runtime in release artifacts (`dist/MediaPlayer/vlc`) so users can run without preinstalled VLC.
- Runtime bootstrap (`src/player/vlc_runtime.py`) to detect local VLC folder and configure DLL/plugin paths on Windows.

### Changed
- Startup flow in `src/main.py` to initialize bundled VLC runtime before loading the app.
- `README.md` with release packaging instructions for GitHub Actions.
- `.gitignore` to ignore local packaging outputs (`build/`, `dist/`, `*.zip`).
