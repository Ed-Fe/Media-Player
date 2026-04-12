# KeyTune

An accessible media player prototype called **KeyTune**, built with **Python**, **wxPython**, and **VLC**.

The project is keyboard-first and screen-reader-friendly, with support for playlists, folder browsing, session restore, and persistent user preferences.

## Status

This project is in active development. The current version already supports day-to-day playback flows, but the codebase is still evolving.

## Highlights

- Embedded VLC playback inside a wxPython window
- Multiple playlists in tabs
- Folder browser with preview support
- Tab-specific equalizer with built-in VLC presets and custom presets
- `.m3u` / `.m3u8` playlist loading and saving
- Session restore for tabs, current item, position, and volume
- Persistent preferences in `settings.json`
- Recent files, folders, and playlists
- Keyboard-first navigation
- Accessibility announcements through screen readers when available

## Requirements

- Python 3.10 or newer
- VLC Media Player installed on the system (development mode)

## Installation

### 1. Clone the repository

Optional if you already have the files locally.

### 2. Create a virtual environment

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python src/main.py
```

## Windows release with bundled VLC

This repository includes a GitHub Actions workflow at `.github/workflows/release-windows.yml`.

When triggered (manually or by pushing a tag like `v1.2.3`), it will:

1. Build the app with PyInstaller
2. Build the external updater with PyInstaller
3. Copy the updater to the release folder
4. Install VLC on the runner
5. Copy the VLC runtime to `dist/MediaPlayer/vlc`
6. Create `MediaPlayer-windows.zip`
7. Generate `MediaPlayer-windows.zip.sha256`
8. Upload the files as workflow artifacts
9. Attach the files to the GitHub Release when running on a tag

The app startup now looks for a local `vlc/` folder before importing `python-vlc`, so the release can run on machines without VLC pre-installed.
The Windows package also includes `MediaPlayerUpdater.exe`, used by the app to apply downloaded updates after the user confirms the installation.

For a repeatable end-to-end updater test flow, see `docs/update-testing.md`.

## Main keyboard shortcuts

- `Space`: play / pause
- `Left` / `Right`: seek backward / forward
- `Up` / `Down`: volume down / up
- `Home` / `End`: jump to start / end of the current media
- `Ctrl+T`: new playlist tab
- `Ctrl+W`: close current media or close an empty tab
- `Ctrl+Shift+W`: close the current tab or playlist directly
- `Ctrl+PageUp` / `Ctrl+PageDown`: previous / next track
- `Ctrl+Shift+E`: open the equalizer tab for the active media tab
- `Ctrl+Tab` / `Ctrl+Shift+Tab`: next / previous tab
- `Ctrl+O`: open media files directly or a local `.m3u` / `.m3u8` playlist
- `Ctrl+Shift+O`: open a folder directly in the folder browser
- `Ctrl+Alt+O`: open media, playlist, or folder in the unified dialog
- `Ctrl+Shift+S`: save current playlist
- `Ctrl+,`: open preferences
- `F1`: open quick keyboard help
- `F6`: switch focus between the item list and the player
- In the item browser, type letters or numbers to jump quickly to matching items
- `T`: announce playback time
- `V`: announce volume
- `S`: announce player status
- `E`: toggle shuffle
- `R`: cycle repeat mode

## Project structure

- `src/main.py` — application entry point
- `src/player/app.py` — wx application bootstrap
- `src/player/frame.py` — main window coordinator
- `src/player/frame_ui.py` — menus, layout, and UI bindings
- `src/player/frame_commands.py` — event handlers and shortcuts
- `src/player/frame_playback.py` — VLC playback logic
- `src/player/frame_library.py` — tabs, playlists, and folder navigation
- `src/player/frame_session.py` — session capture and restore
- `src/player/frame_recents.py` — recent items and path helpers
- `src/player/playlists.py` — playlist state and tab naming helpers
- `src/player/playlist_io.py` — `.m3u` / `.m3u8` load and save helpers
- `src/player/playlist_browser.py` — side panel for playlist and folder navigation
- `src/player/preferences_dialog.py` — preferences UI
- `src/player/settings.py` — persistent user settings
- `src/player/session.py` — session persistence
- `src/player/accessibility.py` — screen reader helpers

## Accessibility notes

- UI labels, status messages, and announcements are currently in **Portuguese**.
- The app is designed to avoid noisy focus on the native VLC output area.
- `accessible-output2` is optional; the app should continue to work without it.

## Contributing

Contributions are welcome.

If you want to help:

1. Fork the repository
2. Create a feature branch
3. Make focused changes
4. Run the quick validation step
5. Open a pull request with a clear description

### Development notes

- Prefer small, targeted changes over broad refactors
- Keep user-facing text in Portuguese unless the project direction changes
- Preserve keyboard-first behavior and accessibility flows
- Try not to introduce mouse-only interactions

### Quick validation

```bash
python -m compileall src
```

### Local Windows release build

To generate a local packaged build for updater testing, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_release.ps1
```

## Roadmap

- Multi-selection in the playlist browser
- Batch reordering support
- More playback and library management features

## Changelog

- See `CHANGELOG.md` for version history and notable changes.
