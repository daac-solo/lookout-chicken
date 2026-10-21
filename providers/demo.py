"""
Demo provider — static sample data.

Exists so `git clone && build && run` produces a working app with no backend,
no config and no network. Anyone evaluating the project sees the thing work
before deciding whether to wire it to their own data.

The numbers are deliberately unflattering: the whole point of the widget is
the uncomfortable one (how long finished work has been sitting), so the demo
should show that rather than a tidy all-clear.
"""


def fetch(cfg=None):
    return {
        "distill": {
            "todayDay": 146,
            "streak": 18,
            "done": False,
            "id": "demo/today",
        },
        "ready": {
            "count": 3,
            "oldestDays": 136,
            "items": [
                {"id": "demo-1", "title": "The one you finished in June"},
                {"id": "demo-2", "title": "Half-remembered draft"},
            ],
        },
        "sparks": {"hot": 4},
        # Lands in the "hungry" band, so a fresh clone shows the mood the
        # chick spends most of its life in rather than a permanent grin.
        # It is static, so the demo chick never actually gets fed.
        "fedHoursAgo": 11.0,
        "library": 141,
        "shelf": 0,
        "demo": True,
    }
