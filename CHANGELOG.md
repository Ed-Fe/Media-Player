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

## [0.1.0] - 2026-04-11

### Added
- Windows release workflow (`.github/workflows/release-windows.yml`) to build and publish a ZIP package.
- Bundled VLC runtime in release artifacts (`dist/MediaPlayer/vlc`) so users can run without preinstalled VLC.
- Runtime bootstrap (`src/player/vlc_runtime.py`) to detect local VLC folder and configure DLL/plugin paths on Windows.

### Changed
- Startup flow in `src/main.py` to initialize bundled VLC runtime before loading the app.
- `README.md` with release packaging instructions for GitHub Actions.
- `.gitignore` to ignore local packaging outputs (`build/`, `dist/`, `*.zip`).
