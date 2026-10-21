"""
Configuration — everything that differs between machines lives here.

The original was wired to one person's setup: a vault path, a private API on
localhost, a token read out of a sibling project's .env. None of that can
survive contact with someone else's computer, so it all moved into a JSON
file that gets written with working defaults on first run.

The defaults use the demo provider, which means a fresh clone launches and
shows something without any backend at all.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "lookout-chicken"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_DIR = Path.home() / ".local" / "share" / "lookout-chicken"

# The shelf and the command file are app state, not configuration — they are
# not things anyone would hand-edit, so they stay out of config.json.
SHELF_FILE = STATE_DIR / "shelf.json"
CMD_FILE = STATE_DIR / "cmd"

DEFAULTS = {
    # "demo"   needs nothing and shows sample data.
    # "folder" reads a directory of markdown files and counts them itself.
    # "http"   calls `http.base_url` and expects the contract in PROVIDERS.md.
    "provider": "demo",

    "folder": {
        # The only setting that matters. Point it at a vault or any folder of
        # markdown; ~ is expanded. It is only ever read, never written.
        "path": "~/Documents/Notes",
        # Frontmatter `status:` (or `state:`) values that mean "finished".
        # Change these to whatever you already write rather than re-tagging
        # a vault to suit the widget.
        "ready_states": ["ready", "scheduled", "done"],
        # Values that mean "a half-thought, still warm".
        "spark_states": ["idea", "spark", "draft"],
        # Directory names to skip anywhere in the tree. Dotfolders are
        # always skipped.
        "ignore": ["templates", "archive", ".obsidian"],
    },

    "http": {
        "base_url": "http://localhost:3456",
        # Sent as the x-access-token header when non-empty. Leave blank for
        # an unauthenticated local service.
        "token": "",
        # Optional: read the token out of a KEY=value file instead of storing
        # it here, so config.json stays safe to share.
        "token_file": "",
        "token_key": "ACCESS_TOKEN",
        # Appended to base_url when the widget is clicked.
        "open_path": "/#today",
    },

    "ui": {
        "language": "zh",          # "zh" or "en"
        "type_sound": True,        # soft keystroke feedback
        "show_widget_on_launch": True,
        "refresh_seconds": 120,
    },

    "hotkeys": {
        # Modifiers are "ctrl", "cmd", "shift", "opt", joined by "+".
        "note": "ctrl+cmd+n",
        "island": "ctrl+cmd+i",
        "ball": "ctrl+cmd+b",
    },
}


def _merge(base, override):
    """Shallow-merge one level deep, so a config that predates a new setting
    still gets the new default rather than a KeyError."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def load():
    try:
        user = json.loads(CONFIG_FILE.read_text())
    except Exception:
        user = {}
    return _merge(DEFAULTS, user)


def write_default_if_missing():
    """Give a first-run user something to edit rather than a blank page."""
    if CONFIG_FILE.exists():
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(DEFAULTS, indent=2, ensure_ascii=False))
    return True


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
