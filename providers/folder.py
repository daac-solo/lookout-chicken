"""
Folder provider — read a directory of markdown files, no server involved.

This is the one that makes the project useful to someone who just cloned it.
The demo provider proves the app runs; this one makes it true, by counting
your own notes. Point it at an Obsidian vault, a Logseq graph, or any plain
folder of markdown with frontmatter and the numbers become yours.

What it computes, and why only these:

  ready        files whose frontmatter state says the work is finished —
               the pile the whole widget exists to make uncomfortable.
  library      how much is in the folder at all. Context, not a debt.
  sparks.hot   recent half-thoughts, which decay fast and are worth
               surfacing while they are still warm.
  fedHoursAgo  how long since anything in the tree changed, which is what
               the chick's mood reads from.

`distill` is deliberately absent: it describes one person's daily writing
practice and would be noise in anyone else's folder. The widget skips
sections it has no data for, so leaving it out costs nothing.
"""

import os
import re
import time
from datetime import date, datetime

# Re-scanning a large vault every refresh is wasteful, and the answer barely
# moves between refreshes. Keep the last result until the tree changes.
CACHE_SECONDS = 25
SPARK_DAYS = 3
MAX_ITEMS = 6
# A frontmatter block is at the top of a file; reading megabytes to find it
# would be silly.
HEAD_BYTES = 4096

_cache = {"key": None, "at": 0.0, "value": None}

_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
_KV = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
_H1 = re.compile(r"^#\s+(.+)$", re.M)
# Logseq writes `key:: value` at the top of a page instead of YAML. Claiming
# Logseq support without this would be a lie, and the cost is one more regex.
_LSQ = re.compile(r"^([A-Za-z_][\w-]*)::\s*(.*)$")
# Logseq wraps dates and references in [[...]]; the value is what is inside.
_LINK = re.compile(r"^\[\[(.*)\]\]$")


def _logseq_properties(text):
    """Read the leading `key:: value` block, which is where Logseq keeps what
    YAML frontmatter holds elsewhere. Stops at the first line that is not a
    property, so page content is never scanned."""
    out = {}
    for line in (text or "").splitlines():
        if not line.strip():
            if out:
                break
            continue
        m = _LSQ.match(line.strip())
        if not m:
            break
        key, raw = m.group(1).strip().lower(), m.group(2).strip()
        link = _LINK.match(raw)
        if link:
            raw = link.group(1).strip()
        if raw:
            out[key] = raw
    return out


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_frontmatter(text):
    """A deliberately small YAML subset: `key: value`, quoted values, and
    `[a, b]` lists. Pulling in a parser for this would mean asking the user
    to install something, which is a worse trade than not handling anchors.

    Anything unparseable is skipped rather than raised — this runs in a menu
    bar app with nowhere to show an error.
    """
    out = {}
    m = _FM.match(text or "")
    if not m:
        return _logseq_properties(text)
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Indented lines belong to a nested structure we do not model.
        if line[:1] in (" ", "\t", "-"):
            continue
        km = _KV.match(line)
        if not km:
            continue
        key, raw = km.group(1).strip().lower(), km.group(2).strip()
        # Strip a trailing comment, but not a `#tag` inside a value.
        if raw.startswith("[") and raw.endswith("]"):
            out[key] = [_unquote(x) for x in raw[1:-1].split(",") if x.strip()]
        else:
            out[key] = _unquote(raw)
    return out


def _as_date(v):
    """Accept the handful of shapes people actually write by hand. A date
    that will not parse is treated as absent, never as an error."""
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    # Tolerate "2026-07-11 4:30pm PST" and ISO timestamps alike by taking
    # the date part and ignoring whatever follows.
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _state(fm):
    """Two spellings in the wild; treat them as the same field."""
    for key in ("status", "state"):
        v = fm.get(key)
        if isinstance(v, (list, tuple)):
            v = v[0] if v else None
        if v:
            # "scheduled 2026-07-11 4:30pm" — the word is the state.
            return str(v).strip().split()[0].lower()
    return ""


def _title(fm, text, path):
    t = fm.get("title")
    if isinstance(t, (list, tuple)):
        t = t[0] if t else None
    if t:
        return str(t)
    m = _H1.search(text or "")
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0]


def _opts(cfg):
    f = (cfg or {}).get("folder") or {}
    return (
        os.path.expanduser(f.get("path") or ""),
        [s.lower() for s in (f.get("ready_states")
                             or ["ready", "scheduled", "done"])],
        [s.lower() for s in (f.get("spark_states")
                             or ["idea", "spark", "draft"])],
        [s for s in (f.get("ignore") or []) if s],
    )


def _walk(root, ignore):
    """Yield every markdown path under root, skipping dotfiles and anything
    the user asked to ignore."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in ignore]
        for name in filenames:
            if name.startswith(".") or not name.lower().endswith((".md", ".markdown")):
                continue
            yield os.path.join(dirpath, name)


def _empty():
    """The honest answer when there is nothing to read: zeros, and no mood.
    Omitting fedHoursAgo keeps the chick neutral rather than blaming the user
    for a path that does not exist."""
    return {"ready": {"count": 0, "oldestDays": 0, "items": []},
            "library": 0, "sparks": {"hot": 0}, "shelf": 0,
            # Lets the widget tell "nothing finished yet" apart from
            # "this number came from somewhere else entirely".
            "source": "folder"}


def _scan(root, ready_states, spark_states, ignore):
    today = date.today()
    now = time.time()
    newest = 0.0
    library = 0
    hot = 0
    ready = []

    for path in _walk(root, ignore):
        library += 1
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0
        newest = max(newest, mtime)

        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                head = fh.read(HEAD_BYTES)
        except OSError:
            continue

        fm = parse_frontmatter(head)
        st = _state(fm)
        if st in ready_states:
            when = _as_date(fm.get("date")) or _as_date(fm.get("created"))
            days = (today - when).days if when else 0
            ready.append({
                "id": os.path.splitext(os.path.relpath(path, root))[0],
                "title": _title(fm, head, path)[:60],
                "days": max(days, 0),
            })
        elif st in spark_states and (now - mtime) <= SPARK_DAYS * 86400:
            hot += 1

    # Oldest first: the top of the list is the thing that has waited longest.
    ready.sort(key=lambda it: -it["days"])
    out = _empty()
    out["library"] = library
    out["sparks"] = {"hot": hot}
    out["ready"] = {
        "count": len(ready),
        "oldestDays": ready[0]["days"] if ready else 0,
        "items": [{"id": it["id"], "title": it["title"]}
                  for it in ready[:MAX_ITEMS]],
    }
    if newest:
        # Hours since the user last touched anything. Scanning does not count
        # as feeding, which is why this reads mtime rather than scan time.
        out["fedHoursAgo"] = max((now - newest) / 3600.0, 0.0)
    return out


def _cache_key(root, ignore):
    """Cheap proxy for "did anything change": the newest mtime in the tree.
    Walking the directory is far cheaper than opening every file."""
    newest = 0.0
    count = 0
    for path in _walk(root, ignore):
        count += 1
        try:
            newest = max(newest, os.path.getmtime(path))
        except OSError:
            pass
    return (count, round(newest, 3))


def fetch(cfg=None):
    root, ready_states, spark_states, ignore = _opts(cfg)
    if not root or not os.path.isdir(root):
        return _empty()
    try:
        now = time.time()
        if _cache["value"] is not None and now - _cache["at"] < CACHE_SECONDS:
            return _cache["value"]
        key = _cache_key(root, ignore)
        if key == _cache["key"] and _cache["value"] is not None:
            _cache["at"] = now
            return _cache["value"]
        value = _scan(root, ready_states, spark_states, ignore)
        _cache.update({"key": key, "at": now, "value": value})
        return value
    except Exception as e:
        # Degrade, never crash: a wrong number is recoverable, a dead menu
        # bar app is not.
        print(f"[folder] scan failed: {e}", flush=True)
        return _cache["value"] or _empty()
