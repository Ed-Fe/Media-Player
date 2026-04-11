# Project Guidelines

## Code Style

- Use Python code consistent with the existing `src/player/*.py` modules: small helpers, explicit names, and dataclasses for persisted state.
- Keep user-facing labels, menu text, status messages, and screen reader announcements in Portuguese.
- Prefer small, targeted edits over broad refactors in the `src/player/frame*.py` modules; `frame.py` coordinates the window and composes focused mixins.

## Architecture

- Entry flow is `src/main.py` -> `src/player/app.py` -> `src/player/frame.py`.
- Keep responsibilities separated:
	- `frame.py` for the main window shell and mixin composition
	- `frame_ui.py` for menus, layout, control setup, and UI bindings
	- `frame_commands.py` for file dialogs, open/save actions, and command handlers
	- `frame_playback.py` for VLC backend setup, playback control, and progress updates
	- `frame_library.py` for playlist tabs, folder navigation, and active tab state
	- `frame_session.py` for session capture and restore
	- `frame_recents.py` for recent items and default path helpers
	- `playlists.py` for playlist/tab state
	- `playlist_io.py` for `.m3u` / `.m3u8` loading and saving
	- `preferences_dialog.py` for the preferences UI
	- `settings.py` for durable user preferences in `settings.json`
	- `session.py` for restorable session state in `session.json`
	- `accessibility.py` for screen reader announcements and custom `wx.Accessible` helpers
- Do not mix durable preferences with session restoration logic; preserve the separation between `settings.py` and `session.py`.

## Build and Test

- Install dependencies from `requirements.txt` in a virtual environment.
- Run the app with `python src/main.py`.
- Use `python -m compileall src` as the quick validation step after Python changes.
- There is no automated test suite yet, so for UI changes do a focused manual check of the affected keyboard flows, dialogs, playlist behavior, and announcements.
- The app depends on VLC being installed on the system.

## Conventions

- This project is keyboard-first and accessibility-first. Preserve existing shortcuts and avoid introducing mouse-only flows.
- Do not force focus changes in dialogs, tab switches, or auxiliary windows unless explicitly requested.
- When touching accessibility, prefer the existing helpers in `src/player/accessibility.py` and keep optional `accessible-output2` integration defensive.
- Preserve behavior that avoids noisy focus on the native VLC output area.
- When changing preferences or session behavior, keep storage paths and JSON formats backward-compatible whenever practical.
- For large new features, after implementation and validation, ask the user whether they want you to create a Git commit before committing anything.
- When the user wants a commit for a large new feature, use a semantic commit message in Conventional Commits style (for example `feat: ...`) and perform the push after the commit.
- For the full feature list and shortcut inventory, see `README.md` instead of duplicating that content here.

## Related Customizations

- Use `.github/instructions/player-ui-a11y.instructions.md` when editing wxPython UI, dialogs, menus, keyboard shortcuts, focus handling, playlist browser, or screen reader accessibility.
- Use `.github/instructions/git-workflow.instructions.md` when finalizing a large feature, preparing a commit, or pushing repository changes.
- Use `.github/prompts/accessibility-smoke-test.prompt.md` for a focused post-change accessibility verification pass after UI or accessibility work.
