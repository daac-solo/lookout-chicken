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
  "shelf": 0
}
```

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
