# 瞭望鸡 · Lookout Chicken

A small macOS companion that keeps one uncomfortable number in front of you:
**how long something you already finished has been sitting unpublished.**

Most capture tools optimise the wrong end. Saving things is easy — the pile
grows on its own. What actually stalls is shipping. So this one stays quiet
about your unread library and loud about the draft you finished in June.

![screenshot placeholder](docs/screenshot.png)

---

## Three forms

It is the same companion in three shapes, each reachable directly by hotkey
so you never click through one to get to another.

| Form | What it is | Default key |
|---|---|---|
| **Card** | A panel with a capture field and the full readout | `⌃⌘N` |
| **Island** | A pill flush under the notch, saying one short thing | `⌃⌘I` |
| **Ball** | A draggable chick that idles with a breathing animation | `⌃⌘B` |

Hover any form for 0.12s and a popup appears beside the cursor with the
detail. Hovering shows; clicking commits. You should never have to click
something just to read it.

### Capture never asks a question

Press `⌃⌘N` anywhere, type, press Enter. The note lands on a local shelf and
the panel gets out of the way. There is no "which folder", no "add a tag", no
"why are you saving this" — a capture that demands justification up front is
a capture you skip when you are busy. The reason can come later, if it comes.

`⇧Enter` sends it straight upstream instead, when a backend is configured.

---

## Install

Requires macOS 13+ and Python 3.11+.

```bash
git clone <your-fork> lookout-chicken
cd lookout-chicken

python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python setup.py py2app

cp -R "dist/Lookout Chicken.app" /Applications/
```

Then sign it with a stable identifier, which matters more than it sounds:

```bash
codesign --force --deep --sign - \
  --identifier com.lookoutchicken.app \
  "/Applications/Lookout Chicken.app"
```

Without a stable identifier, every rebuild looks like a brand new app to
macOS and silently drops the Accessibility grant you are about to give it.
See [NOTES.md](NOTES.md).

### Accessibility permission

The global hotkeys need **System Settings → Privacy & Security →
Accessibility**. Add `Lookout Chicken` and switch it on.

This is not optional and it is not avoidable. macOS only delivers
system-wide key events to a process the user has trusted. The app detects the
grant while running and the warning in its menu disappears on its own — no
restart needed.

If you would rather not grant it, everything except the hotkeys still works;
drive it from the menu bar, or write a word into
`~/.local/share/lookout-chicken/cmd` (`note`, `island`, `ball`, `card`,
`toggle`) from any launcher you already trust.

---

## Pointing it at your own data

On first run it writes `~/.config/lookout-chicken/config.json` and starts on
the **demo provider**, so you see it working before deciding anything.

To use your own data, set `provider` to `http` and give it a base URL:

```json
{
  "provider": "http",
  "http": {
    "base_url": "http://localhost:3456",
    "token_file": "~/.config/myservice/.env",
    "token_key": "ACCESS_TOKEN"
  }
}
```

Your service answers `GET /api/today` with a small JSON object, and
optionally accepts `POST /api/capture`. The full contract — every field is
optional — is in [PROVIDERS.md](PROVIDERS.md). It is about fifteen lines of
JSON; any static file server or three-line script can satisfy it.

Writing a new provider is a module in `providers/` with one `fetch(cfg)`
function.

### Other settings

| Key | Does |
|---|---|
| `ui.language` | `"zh"` (default) or `"en"` |
| `ui.type_sound` | Soft keystroke feedback while typing |
| `ui.show_widget_on_launch` | An ambient reminder you must switch on is one you never switch on |
| `ui.refresh_seconds` | How often to re-fetch (default 120) |
| `hotkeys.*` | `"ctrl+cmd+n"` style strings |

---

## Why a chicken

The number only does its job if you bump into it without looking for it,
which a browser tab can never manage. A small creature that breathes is
harder to ignore than a red badge, and harder to resent than a notification.

It reacts, it never initiates. It does not wander across your screen, grab
your cursor, or interrupt. It sits where you put it and gets slightly more
pointed when something has been waiting too long.

---

## License

MIT — see [LICENSE](LICENSE).

This is a personal tool shared as-is. See [CONTRIBUTING.md](CONTRIBUTING.md).
