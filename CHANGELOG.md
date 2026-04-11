# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 

### Changed
- O aplicativo passou a se chamar **KeyTune** na interface e na documentação principal, sem o sufixo técnico.

### Fixed
- Restauração do volume salvo ao abrir o app com sessão recuperada, aplicando corretamente o nível anterior já no início da reprodução.
- Preservação da posição atual do áudio ao entrar e sair da aba do equalizador, sem voltar para o tempo em que a aba foi aberta.
- Retorno ao modo de foco correto ao fechar o equalizador e eliminação do corte no áudio causado pelo recarregamento desnecessário da mesma mídia.

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
