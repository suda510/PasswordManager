# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PasswordManager is a local-first, offline desktop password manager built with Python and PyQt5. All data is stored locally at `%APPDATA%/PasswordManager/data.enc`. No network connections, no cloud dependencies.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main

# Generate app icons (first time only)
python scripts/generate_icon.py

# Build standalone exe (~40MB)
pyinstaller build.spec
```

## Architecture

### Three-Layer Design

**Core Layer** (`app/core/`) — Pure logic, no UI dependencies:
- `crypto.py` — AES-256-GCM encryption/decryption, PBKDF2 key derivation (600k iterations), master password hashing, recovery key generation
- `db.py` — SQLite database with transparent encrypt/decrypt for sensitive fields. Handles CRUD, CSV export, and `rekey()` for master password changes
- `models.py` — Frozen dataclasses (`Entry`, `Config`) with immutable `with_update()` pattern
- `config_manager.py` — Key-value config table (separate from encrypted data), custom group storage as JSON

**UI Layer** (`app/ui/`) — Pure PyQt5, no external UI frameworks:
- `login_window.py` — Frameless window with master password setup, login, recovery key flow
- `main_window.py` — Main application with entry list, detail panel, group filtering, search
- `dialogs.py` — AddEditDialog and confirm_delete
- `notification.py` — Shared toast notification with slide-in/out animation
- `styles.py` — All QSS styles and constants. `get_combo_style()` handles runtime arrow icon path resolution
- `icon_gen.py` — Programmatic icon generation (app icon, copy, eye)

**Utils Layer** (`app/utils/`):
- `clipboard.py` — Copy with 30-second auto-clear via QTimer
- `paths.py` — Resolves `%APPDATA%/PasswordManager/` data directory

### Key Data Flow

1. **Login**: `LoginWindow` → verify password → derive key via PBKDF2 → emit `login_success(bytes)` → `MainWindow` created with `Database(key)`
2. **Encryption**: All sensitive fields (username, password) encrypted with AES-256-GCM before SQLite storage, decrypted on read
3. **Master Password Change**: `db.rekey(new_key)` re-encrypts all entries in a transaction, then forces logout/re-login
4. **Groups**: Stored as a JSON array in config table (`custom_groups`). Groups also exist implicitly as entry attributes. `_get_all_groups()` merges both sources.

### Window Lifecycle (main.py)

```
create_login_window() → LoginWindow
  ├── login_success → close login, create Database + MainWindow
  │     └── logout signal → close main + db, recreate login
  └── need_restart → close login, recreate ConfigManager, recreate login
```

## Critical Security Constraints

- **Never log or print passwords or encryption keys**
- `config.get()` returns `None` when keys don't exist — always use `config.get_salt()` and `config.get_iterations()` which handle None safely
- Changing master password requires `db.rekey()` to re-encrypt all data — skipping this causes permanent data loss
- Recovery key reset cannot re-encrypt (old password unknown) — user is warned before proceeding
- Clipboard auto-clear runs on QTimer (30s) — survives app exit via `app.aboutToQuit`

## UI Patterns

- **Toast notifications**: Use `from app.ui.notification import show_toast` — never create ad-hoc QLabel notifications
- **Dialogs**: All QDialogs must set `~Qt.WindowContextHelpButtonHint` to remove the "?" button. Use `parent=None` to avoid style inheritance issues, then `move()` to center on parent
- **Custom popup**: QComboBox dropdown uses a custom `QWidget(Qt.Tool | FramelessWindowHint)` popup with rounded corners via stylesheet — the native Qt popup cannot be styled with border-radius
- **Fonts**: Global font is `Microsoft YaHei 11px` set in `main.py`
- **Styles**: All QSS in `styles.py`. Use `get_combo_style()` for combo boxes (resolves arrow icon path at runtime)

## PyInstaller Packaging

- `build.spec` excludes ~40 unused PyQt5 modules (QtWebEngine, QtMultimedia, Qt3D, etc.) to reduce size
- `assets/` directory is bundled via `datas` for the arrow icon
- Output: `dist/PasswordManager.exe` (~40MB)
