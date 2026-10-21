# The data contract

The widget renders one dict. Where it comes from is the only thing most
people need to change, so it is the only thing that is pluggable.

**Every field is optional.** The widget skips any section it has no data
for, so a provider returning a single key is valid — it just shows less.

```jsonc
{
  // A daily streak. Omit the whole object if you have no such habit.
  "distill": {
    "todayDay": 146,      // day number, shown as "Day 146"
    "streak": 18,         // consecutive days
    "done": false,        // done today? drives the colour
    "id": "2026-10-20"    // optional, for deep links
  },

  // Finished but unpublished. This is the one the app exists for.
  "ready": {
    "count": 3,
    "oldestDays": 136,    // turns terracotta past 30
    "items": [            // at most two are shown
      { "id": "draft-1", "title": "The one you finished in June" }
    ]
  },

  // Ideas still worth acting on.
  "sparks": { "hot": 4 },

  // Unread material. Deliberately shown in the faintest grey available:
  // a library is a resource, not a debt, and rendering it as a todo count
  // is how an inbox becomes a source of guilt.
  "library": 141,

  // Items staged locally but not yet filed.
  "shelf": 0,

  // Hours since anything last went into the system. This is the only field
  // the chick's own state reads from: under 0.5 it is fed and lively, under
  // 6 settled, under 24 hungry, beyond that droopy. Omit it and the chick
  // stays neutral — better than a provider that cannot tell and so implies
  // neglect.
  "fedHoursAgo": 11.0
}
```

## The `folder` provider

Reads a directory of markdown files and computes the numbers itself. No
server, no network, no plugin. It only ever reads — it never writes to your
files.

```jsonc
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

| key | meaning |
| --- | --- |
| `path` | the folder to scan, recursively. `~` is expanded. |
| `ready_states` | frontmatter `status:` (or `state:`) values that mean "finished". Set these to whatever you already write. |
| `spark_states` | values that mean "a half-thought". Counted in `sparks.hot` only if the file changed in the last three days. |
| `ignore` | directory names skipped anywhere in the tree. Dotfolders and dotfiles are always skipped. |

How each field is derived:

- **`ready`** — files whose state is in `ready_states`. `oldestDays` is today
  minus the earliest `date:` or `created:` among them; a date that will not
  parse counts as zero days rather than throwing the scan away. `items` carry
  the path relative to `path` without its extension as `id`, and `title:`,
  else the first `# heading`, else the filename as `title`. Oldest first.
- **`library`** — every `.md` file scanned, classified or not.
- **`sparks.hot`** — `spark_states` files modified within three days.
- **`fedHoursAgo`** — hours since the newest mtime in the tree. It reads
  mtime rather than scan time on purpose: a refresh is not a meal.
- **`source`** — the literal string `"folder"`. The widget uses it to tell a
  real "nothing finished yet" apart from a number that came from somewhere
  else, so it can explain a zero instead of just showing one. Report it from
  your own provider only if you want that same explanation; the key is
  otherwise ignored.
- **`distill`** — not reported. It describes one person's daily writing
  habit, and the widget skips the section when it is absent.

Two property formats are read. YAML frontmatter between `---` fences, in a
small subset: `key: value`, quoted values, and `[a, b]` lists. And Logseq's
leading `key:: value` block, including its `[[date]]` links. `.md` and
`.markdown` are scanned; a file with neither format still counts toward
`library` but cannot be classified.

The scan is cached and only repeats when the newest mtime in the tree changes,
so pointing it at a large vault does not cost anything on every refresh. A
path that does not exist returns zeros, not an error.

## Writing (optional)

A provider may also expose `capture(cfg, text, why="")`, returning
`(ok, message)`. `message` is shown to the user on success, so make it say
*where the note went* — that is the only thing teaching the difference
between `Enter` (the shelf) and `⇧Enter` (your notes).

`folder` implements it by writing a new file into `folder.inbox` with
`status: <capture_state>` frontmatter, so the note it just wrote is counted
by the next read. It never edits or deletes an existing file, and it never
overwrites: a colliding filename gets a `-2` suffix.

A provider without `capture` is read-only, and `⇧Enter` falls back to the
local shelf rather than failing.

## Endpoints (the `http` provider)

### `GET /api/today`

Returns the object above. Sent with `x-access-token` when a token is
configured. A non-200, a timeout, or malformed JSON is treated as "no data"
— the widget keeps showing what it last had rather than flashing an error.

### `POST /api/capture` — optional

```json
{ "text": "the note", "why": "" }
```

Expected back:

```json
{ "ok": true, "kind": "idea" }
```

`kind` is echoed in the confirmation. On `ok: false`, include `error` with a
short string; it is shown in the capture field.

Without this endpoint, `⇧Enter` simply falls back to the local shelf.

## Writing your own provider

A module in `providers/` with one function:

```python
def fetch(cfg):
    """Return the dict above, or None when there is nothing to show."""
    return {"ready": {"count": 1, "oldestDays": 42}}
```

Register it in `providers/__init__.py` and name it in your config. Returning
`None` is fine and expected — it means "no data right now", not an error.

Two rules worth honouring, because they are what keep the thing liveable:

- **Never raise.** The widget repaints on a timer; an exception there is a
  crash loop. Catch and return `None`.
- **Be fast.** `fetch` runs on the main thread. If your source is slow,
  cache it and return the cached value.
