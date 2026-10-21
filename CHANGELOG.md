# Changelog

Every release says what changed and, where it is not obvious, why. Dates are
the day the work landed. This project follows [semantic versioning]
(https://semver.org): until `1.0.0` the minor number moves when behaviour
changes and the patch number when something is repaired.

## [Unreleased]

### Added

- **It walks over and eats.** Grain lands to one side, one at a time with a
  tick as each settles; the chick notices, hops over, eats them one per
  peck, says something, and hops back. Pecking on the spot read as a twitch
  — the reward for putting something in should be a small story.
- **A keystroke and a grain have different sounds**, both synthesised rather
  than borrowed, because no system sound has anything below 1kHz.

### Fixed

- **Hovering never did anything.** The widget is a non-activating panel, and
  macOS does not deliver mouse-moved events to one while the app is in the
  background — so no tracking area on it could ever fire, no matter which
  options it carried. Clicks arrive by a different route, which is why the
  chick reacted to a click and ignored the pointer. Hover is now computed
  from `NSEvent.mouseLocation()`, which does work from the background, on a
  timer that runs only while the panel is visible.
- **The grain was invisible.** Gold on paper measures 2.1:1, at 3.5pt. Ochre
  at 4.7:1, 6×4 and oval, is something you can see lying on a page.
- **Animation groups do not pass their duration to their children.** Left at
  zero, each sub-animation ran for CoreAnimation's default quarter second
  and snapped back — which looks exactly like the chick never moving.

- **A failed capture no longer looks like a broken Enter key.** PyObjC
  swallows exceptions raised inside a delegate method, so anything going
  wrong when you pressed Enter produced no sound, no error and no saved
  note — indistinguishable from the key not being wired up. Whatever breaks
  now says so in the field and leaves your text there to retry, with the
  traceback in `~/.local/share/lookout-chicken/error.log`.

### Changed

- **The confirmation names where the note went** — *wrote inbox/….md*, or
  *on the shelf · not in your notes yet* — instead of a generic "saved".
  Two keys send to two different places, and without this there is no way
  to tell which one happened.

### Added

- `pick` joins the command-file verbs, so the folder picker can be opened
  from a launcher or a script rather than only from the menu. It is also
  what makes the picker testable without a human clicking a menu item —
  which is why the UI path went unverified in 0.1.0.

## [0.1.0] — 2026-10-21

First release. Extracted from a personal tool and made to work on somebody
else's machine.

### The idea

Every PKM system is built to capture, and almost none of them tell you what
is rotting. A vault shows folders, tags, graphs and backlinks — every
representation of what you *have*, and none of the one thing that matters:
the note you finished and never did anything with. A query that computes it
is a query you stop running. This keeps the number in front of you instead.

### Added

- **Folder provider.** Point it at any directory of markdown and it counts
  your own notes — finished-but-unpublished, how long the oldest has waited,
  how much is in the library, how many half-thoughts are still warm. No
  plugin, no sync, no account, no index.
- **Two property formats.** YAML frontmatter and Logseq's `key:: value`,
  including its `[[date]]` links. `.md` and `.markdown`.
- **`ready_states` adapts to you.** Finished notes that say `published`, or
  `完成`, or anything else, count — nobody re-tags a vault to suit a widget.
- **Setup by folder picker.** First launch offers one, and the menu keeps
  it. No hand-editing JSON inside a hidden directory.
- **Capture lands in the vault.** `⌃⌘N` anywhere, type, `⇧Enter`, and the
  thought is a markdown file in a folder you name, with frontmatter the
  provider reads back — so it returns as *"3 ideas still warm"* in your own
  notes app. Plain `Enter` parks it on a local shelf instead, because half
  of what anyone grabs in a hurry is not worth keeping.
- **Pasted links are filed under something readable.** The address goes to
  `source:`; a bare link is named for its host, a link with a thought beside
  it is named for the thought.
- **Moods.** The chick reads how long since anything in your folder changed,
  and gets hungry, then droopy. Writing feeds it.
- **Three forms.** A card, a pill under the notch, and a pet you can drag
  anywhere, on `⌃⌘N` / `⌃⌘I` / `⌃⌘B`.
- **A keystroke with a body.** Synthesised rather than borrowed: every
  system sound macOS offers is a high beep with nothing underneath it,
  which is why typing felt flimsy at any volume.
- **`demo-vault/`** — fourteen invented notes, so the provider can be
  verified before it is pointed at anything you care about.
- **`check.sh`** — compiles, checks both string tables, reads the demo
  vault, confirms bad input degrades to zeros, and launches the bundled
  binary.

### Fixed

- **A zero no longer means four different things.** A wrong path, states
  that do not match your vault, and notes without frontmatter all rendered
  as `0`, which reads as "this tool does not work". Each says which it is,
  and that line reopens the picker.
- **A broken config says so.** It used to fall back to demo data silently —
  sample numbers that look exactly like a working app.
- **Logseq actually works.** The README claimed it; the parser only read
  YAML, so every Logseq note fell through unclassified.
- **The artwork shows up when run from source.** Resource lookup only
  checked the app bundle, so `python chicken.py` degraded to an emoji —
  which read as "this is what it looks like".
- **The chick no longer survives its own form change.** The pet drew
  straight into the sheet while the card only cleared its own container, so
  expanding from the ball left a second chick parked in the corner.

### Notes

- There is no prebuilt download. A downloaded app is quarantined unless
  notarized, and notarization needs a paid Apple Developer account; an app
  you compile yourself opens without any of that, and can be read first.
- The chick artwork is the author's own mark and is not covered by the MIT
  licence. Replace it if you publish a fork as its own product.
