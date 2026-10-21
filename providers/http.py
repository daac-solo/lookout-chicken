"""
HTTP provider — point it at any service that speaks the contract.

GET  {base_url}/api/today    -> the dict described in PROVIDERS.md
POST {base_url}/api/capture  -> {"text": ..., "why": ...}, returns {"ok": ...}

Both are optional: a backend that only serves /api/today still works, capture
just reports the failure instead of silently dropping the note.
"""

import json
import urllib.error
import urllib.request

TIMEOUT_READ = 10
TIMEOUT_WRITE = 15


def _token(cfg):
    """Prefer an inline token, fall back to reading a KEY=value file.

    The file indirection exists so config.json can be committed or shared
    without carrying a credential in it.
    """
    h = (cfg or {}).get("http") or {}
    if h.get("token"):
        return h["token"]
    path = h.get("token_file")
    if not path:
        return ""
    key = h.get("token_key") or "ACCESS_TOKEN"
    try:
        import os
        with open(os.path.expanduser(path), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def _headers(cfg, extra=None):
    out = dict(extra or {})
    tok = _token(cfg)
    if tok:
        out["x-access-token"] = tok
    return out


def base_url(cfg):
    return ((cfg or {}).get("http") or {}).get("base_url") or ""


def open_url(cfg):
    h = (cfg or {}).get("http") or {}
    return (h.get("base_url") or "") + (h.get("open_path") or "")


def fetch(cfg):
    url = base_url(cfg)
    if not url:
        return None
    req = urllib.request.Request(f"{url}/api/today", headers=_headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_READ) as r:
            return json.loads(r.read())
    except Exception:
        return None


def capture(cfg, text, why=""):
    """Send one note upstream. Returns (ok, short_message)."""
    url = base_url(cfg)
    if not url:
        return False, "no backend configured"
    body = json.dumps({"text": text, "why": why}).encode()
    req = urllib.request.Request(
        f"{url}/api/capture", data=body, method="POST",
        headers=_headers(cfg, {"Content-Type": "application/json"}))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_WRITE) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return False, str(data.get("error", "failed"))
        return True, str(data.get("kind") or "saved")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:60]
