"""
Build Lookout Chicken as a real .app.

The point is not packaging for its own sake: Accessibility permission is
granted per-binary, and a bare script means granting it to "Python" — which
is both unnerving and shared with every other Python tool on the machine. A
bundle makes the grant specific to this app.

    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
    ./.venv/bin/python setup.py py2app

Then sign with a stable identifier so the grant survives rebuilds — see
NOTES.md, this one bites hard.
"""

from pathlib import Path

from setuptools import setup

# Single source of truth: the tag, the changelog heading and the bundle all
# read this file, so a release cannot ship a version that disagrees with
# the one it claims.
VERSION = (Path(__file__).parent / "VERSION").read_text().strip()

APP = ["chicken.py"]
ICON = "AppIcon.icns"

OPTIONS = {
    "iconfile": ICON,
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Lookout Chicken",
        "CFBundleDisplayName": "Lookout Chicken",
        "CFBundleIdentifier": "com.lookoutchicken.app",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        # Menu bar only: no Dock tile, no app switcher entry.
        "LSUIElement": True,
        "NSHumanReadableCopyright": "",
        "NSAppleEventsUsageDescription":
            "Lookout Chicken uses system events for its global shortcuts.",
    },
    "packages": ["rumps", "providers"],
    # keysound is imported inside a try block at runtime, which modulegraph
    # does not follow — without naming it here the key sound works from
    # source and silently vanishes in the bundle.
    "includes": ["widget", "popup", "hotkeys", "config", "strings",
                 "keysound", "wave", "array",
                 "ApplicationServices", "Quartz"],
    # These ship with the system; bundling them bloats the app and can
    # conflict with the OS copies.
    "excludes": ["setuptools", "pip", "wheel", "py2app"],
    "resources": ["logo/chick-72.png", "logo/chick-72@2x.png",
                  "logo/chick-18.png", "logo/chick-18@2x.png",
                  "logo/menubar.png", "logo/menubar@2x.png"],
}

setup(
    name="Lookout Chicken",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
