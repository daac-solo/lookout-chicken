# 瞭望鸡 · Lookout Chicken

Every note-taking system is built for putting things in. Almost none of them
tell you what is going stale. Your vault can show you folders, tags, a graph,
backlinks — every one of those describes what you *have*. None of them
surface the note you finished and then never did anything with.

A Dataview query can compute that number. But a query you have to remember to
run is a query you stop running after a week. The number only works if it
comes and finds you.

So: a small creature that lives outside the vault and keeps one number in
front of you, so the piece you finished in June does not quietly become the
piece you finished last year.

It reads a plain folder of markdown — no plugin, no sync, no account, no
index to rebuild.

It is also the fastest way in: `⌃⌘N` anywhere, type, Enter, and the thought
is a markdown file in your vault before the panel has finished closing. One
creature on both ends of the loop — what you put in, and what you never did
anything with.

**It never edits or deletes anything you wrote.** The only thing it ever
writes is a new file, in one folder you name, when you ask it to save a
thought. Nothing else in the vault is touched.

## What it needs from your folder

**No structure at all.** Point it at a directory and it walks everything
beneath: flat, nested, one folder per year, Obsidian's vault layout, Logseq's
`pages/` and `journals/` — all the same to it. Dotfolders like `.obsidian`
and `.git` are skipped, and you can name others to ignore.

What it does need is **one line per note saying the work is finished**, in
either of the two formats people actually use:

```markdown
---
status: ready
date: 2026-06-06
---
```

```markdown
status:: ready
date:: [[2026-06-06]]
```

The first is YAML frontmatter (Obsidian, Foam, Quartz, Jekyll, most static
site generators). The second is Logseq's property syntax. Files ending in
`.md` and `.markdown` are read; everything else is ignored.

`date:` is optional — without it a note still counts as finished, it just has
no age, so it cannot be the one that has waited longest.

Notes with neither are counted in the library total and nothing more. That
includes **Bear and Apple Notes exports, which carry no properties at all** —
they will show up as a library count with zero finished pieces until you add
a status line to the ones you care about. Nothing is wrong when that happens;
there is simply nothing in the files to read.

![The card, the notch pill, and the pet, in that order](docs/demo.gif)

*Card → tucked under the notch → loose on the desktop. The numbers come from
the `demo-vault/` in this repo, not from a real one.*

Requires macOS 13+ and Python 3.11+.

---

## Quickstart

```bash
git clone https://github.com/daac-solo/lookout-chicken && cd lookout-chicken
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python setup.py py2app
open dist/*.app
```

A chick appears in the top-right of your screen, reciting sample numbers,
and offers to point itself at your notes. Decline and it stays on demo data
— you can choose a folder from the menu bar whenever you like.

The first command may pause while macOS installs the Xcode command line
tools. That is a one-off, and it is Apple's prompt, not this project's.

### Why there is no download link

There is no prebuilt `.app` to download, and that is deliberate rather than
unfinished.

A Mac app downloaded from the internet is quarantined by Gatekeeper unless
it has been **notarized** — and notarization requires a paid Apple Developer
Program membership ($99/year). Without it, every person who downloaded a
release would meet *"Apple could not verify this app is free of malware"*
and have to be talked through overriding it. That is a poor first contact
with a tool asking to read your notes.

Building from source sidesteps this completely: an app you compiled yourself
is never quarantined, so it simply opens. It also means **you can read what
you are running** before you run it, which for something pointed at a
personal vault is the better arrangement anyway.

If this project ever gets enough users that compiling is the thing standing
in their way, that is the moment to reconsider — not before.

**If someone hands you a built copy** (AirDrop, a zip, a shared drive),
macOS *will* quarantine that one. Open it the first time with right-click →
**Open** → **Open**, or allow it under System Settings → Privacy & Security.
After the first launch it opens normally. Applying that override to software
from a stranger is a real decision; build it yourself if you would rather
not make it.

---

## Point it at your own notes

This is the step that makes it real, and it does not involve a text editor.

**Menu bar → Choose notes folder…** — pick the folder, and the chick reports
what it found: how many notes, and how many of them are finished and still
unpublished. The same offer appears by itself on first launch.

If it says **no markdown here**, or **notes found but none marked
finished**, that line is a button: it reopens the picker. A zero is always
explained rather than left to look like a broken app.

### The config file, for the settings the picker does not cover

Everything is stored in `~/.config/lookout-chicken/config.json`, which you
are free to edit directly — the picker only writes `provider` and
`folder.path`:

```json
{
  "provider": "folder",
  "folder": {
    "path": "~/Documents/Notes",
    "ready_states": ["ready", "scheduled", "done"],
    "spark_states": ["idea", "spark", "draft"],
    "ignore": ["templates", "archive", ".obsidian"]
  }
}
```

`path` is your vault, or any folder of markdown. It is scanned recursively;
`~` is expanded; dotfiles and dotfolders are skipped.

`ready_states` is the part worth reading twice: **these are whatever you
already use.** If your finished notes say `status: published`, or
`state: 完成`, put that in the list. Nobody is going to re-tag a vault to
suit a widget, so the widget adapts instead.

The config is re-read on the next refresh (default every two minutes). If you
would rather not wait, quit from the menu bar and `open` it again.

### Try it without touching your vault

The repo ships a `demo-vault/` — fourteen invented markdown notes, four of
them finished and unpublished, the oldest dated June. Point the config at it
first if you want to confirm the provider works before aiming it at anything
you care about:

Choose it with the picker like any other folder: it is the `demo-vault`
directory inside this repo.

You should see **4 finished · 14 in library**, with the oldest one well
past a hundred days — it is dated June, so the number grows on its own. If
you do, the only thing left is to change the path.

It is also worth opening a few of those files: they are commented to show
what the parser does and does not understand, including one note with no
frontmatter at all, which is counted but unclassifiable.

### What it looks for in a file

One `status:` (or `state:`) line in the frontmatter is the whole requirement:

```markdown
---
title: The one I finished in June
status: ready
date: 2026-06-06
---
```

That file counts as finished-but-unpublished, and `date:` (or `created:`) is
what makes it *136 days old* rather than just one of three.

If you do not currently mark finished notes at all, you do not have to go
through the vault. Adding one `status:` line to the handful you actually care
about is enough to start.

One honest limitation: it reads frontmatter, so a note with no frontmatter
counts toward the library total but cannot be classified. If every number
comes back zero, that is usually why.

The full contract, and the other providers, are in
[PROVIDERS.md](PROVIDERS.md).

---

## Accessibility permission

**The hotkeys will silently do nothing until you grant this.** No error, no
dialog — the keys simply have no effect. It is the most likely place to
conclude the app is broken when it is not.

**System Settings → Privacy & Security → Accessibility** → add
`Lookout Chicken` and switch it on. The app notices the grant while running;
the warning in its menu disappears on its own, no restart needed.

macOS grants this **per binary**, which means a rebuild looks like a
different app and silently drops the grant. Sign with a stable identifier
after every rebuild and the grant survives:

```bash
codesign --force --deep --sign - \
  --identifier com.lookoutchicken.app \
  dist/*.app
```

Do this before moving it to `/Applications` (and again on the copy there, if
you grant permission to that one). See [NOTES.md](NOTES.md) for why this is
the way it is.

If you would rather not grant it at all, everything except the hotkeys still
works: drive it from the menu bar, or write a word into
`~/.local/share/lookout-chicken/cmd` (`note`, `island`, `ball`, `card`,
`toggle`) from any launcher you already trust.

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
something just to read it. (The card is the exception, and deliberately: it
is already showing everything the popup would say, so hovering it does
nothing.)

### It is also the door in

Watching is half of it. The other half is that the same panel is the fastest
way to get something *into* the vault it is watching.

Press `⌃⌘N` anywhere, type, press Enter. There is no "which folder", no "add
a tag", no "why are you saving this" — a capture that demands justification
up front is a capture you skip when you are busy. The reason can come later,
if it comes.

Two destinations, because not everything you grab deserves to be kept:

| | goes to | for |
|---|---|---|
| `Enter` | a local shelf | the link you grabbed in a hurry, to sort later |
| `⇧Enter` | your notes folder | the thought you already know is worth keeping |

`⇧Enter` writes a real markdown file into a subfolder of your vault —
`inbox/` unless you name another — with frontmatter the provider itself
understands:

```markdown
---
status: spark
created: 2026-10-21
---

the thing you typed
```

So it comes straight back as *"3 ideas still warm"*, in the same vault, in
your own notes app. Nothing is parked in a format only this tool can read.

The shelf is deliberately **not** your vault. Half of what anyone grabs in a
hurry turns out not to be worth keeping, and a vault that collects
everything stops being a library — which is the failure this whole app
exists to notice.

Set `folder.inbox` to `""` to write into the top of the vault instead, and
`folder.capture_state` to whatever word you use for a half-thought.

### It gets hungry

The chick wears how long it has been since you last put anything in. This is
the only state it has that you can change, which is what makes feeding it
mean something.

| Since last capture | Mood | How it looks |
|---|---|---|
| under 30 min | fed | bouncing, head cocked |
| under 6 h | settled | slow breathing |
| under 24 h | hungry | slower, head down, dimmer |
| over 24 h | droopy | barely moving, clearly drooping |

Save something and five grains of rice drop; it pecks once per grain, perks
up, and resets to fed. Hover it and it tilts to look at you. Poke it and it
startles.

This needs a provider that reports `fedHoursAgo`. The `folder` provider reads
it from the newest file in your vault. The demo provider reports a fixed
value, so the demo chick is permanently a little hungry and never gets fed.

The rule it follows throughout: **react, never initiate.** It responds to
things you were already doing and never performs on its own schedule — the
difference between a companion and a distraction.

### Nothing interrupts

It is a non-activating panel, so the app you are in never loses focus. The
confirmation happens in the field's own placeholder rather than a system
notification, because a notification is one more thing to dismiss. It never
redraws while you are mid-sentence, so a half-written thought cannot be lost
to a refresh.

---

## Other providers

| `provider` | Reads from |
|---|---|
| `demo` | Nothing. Static sample numbers, the default. |
| `folder` | A directory of markdown, as above. |
| `http` | Any service answering `GET /api/today`. |

The `http` provider exists for people who already run something — a server, a
script, a cron job writing JSON to a static file:

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

It is about fifteen lines of JSON; any static file server can satisfy it.
Writing a new provider is a module in `providers/` with one `fetch(cfg)`
function. See [PROVIDERS.md](PROVIDERS.md).

### Other settings

| Key | Does |
|---|---|
| `ui.language` | `"zh"` (default) or `"en"` |
| `ui.type_sound` | Soft keystroke feedback while typing |
| `ui.show_widget_on_launch` | An ambient reminder you must switch on is one you never switch on |
| `ui.refresh_seconds` | How often to re-fetch (default 120) |
| `hotkeys.*` | `"ctrl+cmd+n"` style strings |

---

## Troubleshooting

**The hotkeys do nothing.** Accessibility has not been granted, or it was
granted to a previous build. See
[Accessibility permission](#accessibility-permission) above, and re-sign with
a stable identifier after every rebuild.

**A "Launch error" dialog, or it opens and immediately quits.** The bundle
swallows the traceback. Run the binary directly to see it:

```bash
./dist/*.app/Contents/MacOS/*
```

**Every number is zero.** Three things to check, in order: that
`folder.path` points where you think it does (`~` is expanded, but a typo is
not); that the frontmatter values in your notes actually appear in
`ready_states`; and that the notes in question have frontmatter at all — a
note without it is counted in the library total but cannot be classified.

**The chick never gets hungry, or never gets fed.** The mood comes from
`fedHoursAgo`, and only a provider that reports it can drive the mood. The
demo provider returns a fixed value on purpose, so it is always mildly
hungry. Switch to `folder` or report the field yourself.

**macOS says it cannot verify the app.** You are running a copy someone
sent you rather than one you built. Right-click the app → **Open** →
**Open**, or allow it in System Settings → Privacy & Security. See
[Why there is no download link](#why-there-is-no-download-link).

**It is in the way.** Drag it anywhere by its background. `⌃⌘I` parks it
under the notch, `⌃⌘B` shrinks it to the ball, `⌃⌘N` brings the card back.

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
