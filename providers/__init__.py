"""
Data providers.

The widget renders one dict. Where that dict comes from is the only thing a
new user actually needs to change, so it is the one thing that is pluggable.

See PROVIDERS.md for the shape. Every field is optional — the widget skips
sections it has no data for, so a provider can return as little as one key.
"""

from . import demo, folder, http

_BY_NAME = {
    "demo": demo,
    "folder": folder,
    "http": http,
}


def get(cfg):
    """Return a fetch() callable for the configured provider.

    Falls back to demo rather than failing: a companion that silently refuses
    to appear is worse than one showing sample data.
    """
    name = (cfg or {}).get("provider") or "demo"
    mod = _BY_NAME.get(name)
    if mod is None:
        print(f"[provider] unknown provider {name!r}, using demo", flush=True)
        mod = demo
    return lambda: mod.fetch(cfg)
