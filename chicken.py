#!/usr/bin/env python3
"""
瞭望鸡 / Lookout Chicken — a small desktop companion that watches what you owe.

It keeps one uncomfortable number in front of you: how long something you
already finished has been sitting unpublished. Everything else it shows is
quieter on purpose — an unread library is not a debt, and a counter that only
goes up stops being read by the second week.

Three forms, each reachable directly by hotkey:
  card    a panel with a capture field and the full readout
  island  a pill flush under the notch, saying one short thing
  ball    a draggable chick that idles with a breathing animation

Capture never asks a question. Enter files the thought; the reason can come
later, if it comes at all — a capture that demands justification up front is
a capture you skip when you are busy.
"""

import json
import subprocess
from datetime import datetime

import AppKit
import objc
import rumps

import config
import menubar
import providers
import strings
import widget
from hotkeys import HotKeys, describe, trusted
from strings import t
from widget import Widget

MAX_ITEMS = 50


# ---------- shelf storage ----------

def load_shelf():
    try:
        return json.loads(config.SHELF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_shelf(items):
    """Write the shelf without ever being able to destroy it.

    write_text() uses the locale encoding, which inside a py2app bundle is
    ASCII — so a note in any non-Latin script raised UnicodeEncodeError. And
    because write_text truncates before it encodes, that failure emptied the
    file instead of leaving it alone. Hence both an explicit encoding and a
    temporary file that only replaces the real one once it is complete.
    """
    config.ensure_state_dir()
    tmp = config.SHELF_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(config.SHELF_FILE)


def add_to_shelf(text):
    """Local staging. Works with no backend at all, which is the point —
    the shelf is where something goes before you have decided anything."""
    items = load_shelf()
    if any(i.get("text") == text for i in items):
        return True, t("already_shelved")
    items.insert(0, {"text": text,
                     "at": datetime.now().isoformat(timespec="seconds")})
    save_shelf(items[:MAX_ITEMS])
    return True, t("shelved_short")


# ---------- main menu ----------

def install_edit_menu():
    """Standard text editing routes through the main menu bar. A rumps app
    has none, so ⌘A / ⌘C / ⌘V / ⌘Z silently do nothing inside our fields."""
    app = AppKit.NSApplication.sharedApplication()
    if app.mainMenu() is not None:
        return
    main = AppKit.NSMenu.alloc().init()

    app_item = AppKit.NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_menu = AppKit.NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_(
        t("menu_app_quit"), "terminate:", "q")
    app_item.setSubmenu_(app_menu)

    edit_item = AppKit.NSMenuItem.alloc().init()
    main.addItem_(edit_item)
    edit = AppKit.NSMenu.alloc().initWithTitle_("Edit")
    for key, sel, equiv in (
        ("edit_undo", "undo:", "z"),
        ("edit_redo", "redo:", "Z"),
        (None, None, None),
        ("edit_cut", "cut:", "x"),
        ("edit_copy", "copy:", "c"),
        ("edit_paste", "paste:", "v"),
        ("edit_select_all", "selectAll:", "a"),
    ):
        if key is None:
            edit.addItem_(AppKit.NSMenuItem.separatorItem())
            continue
        edit.addItemWithTitle_action_keyEquivalent_(t(key), sel, equiv)
    edit_item.setSubmenu_(edit)

    app.setMainMenu_(main)


# ---------- app ----------

class ChickenApp(rumps.App):
    def __init__(self):
        # Read before anything else writes a default file, so a genuinely
        # first launch is still recognisable further down.
        self._first_run = config.is_first_run()
        self.cfg = config.load()
        self._config_error = config.LAST_ERROR
        strings.use((self.cfg.get("ui") or {}).get("language", "zh"))

        keys = self.cfg.get("hotkeys") or {}
        self.note_key = describe(keys.get("note")) or "⌃⌘N"
        widget.configure(self.cfg.get("ui"), self.note_key)

        icon = AppKit.NSBundle.mainBundle().pathForResource_ofType_(
            "menubar", "png")
        super().__init__("", icon=icon, quit_button=None)
        install_edit_menu()

        self.fetch = providers.get(self.cfg)
        self.items = load_shelf()
        self._stamp = self.file_stamp()
        # rebuild() reads this, and rebuild() runs before the timers start.
        self._trusted = trusted()

        # Build the widget before the first rebuild(): the menu reads its
        # state to label its own items.
        self.widget = Widget.alloc().initWithOpener_handlers_(
            self.open_dashboard,
            {"shelf": self._shelf_then_refresh,
             "flow": self._send_then_refresh,
             "pick": self.pick_folder})

        self.rebuild()

        # The bird in the menu bar reads the same mood the panel does. It is
        # the only part of this app you see without asking, so it carries
        # the one fact worth glancing at: whether anything is owing.
        # rumps builds the status item inside run(), so this cannot happen
        # here — a one-shot timer is the first moment it exists.
        self.bird = None
        self._bird_icon = icon
        rumps.Timer(self._start_bird, 0.4).start()

        # External tools write the same file, so watch it rather than making
        # those paths talk to this process.
        rumps.Timer(self.poll_file, 2).start()
        rumps.Timer(self.poll_cmd, 0.6).start()
        # Permission is granted in System Settings while we are running, so
        # poll for it rather than making the user restart the app.
        rumps.Timer(self.poll_trust, 3).start()

        ui = self.cfg.get("ui") or {}
        if ui.get("show_widget_on_launch", True):
            # An ambient reminder you have to go switch on is one you never
            # switch on.
            self.toggle_widget(None)

        self.install_hotkeys(keys)

        # The waiting-days number is the point, and it only changes slowly.
        rumps.Timer(self.refresh_widget,
                    int(ui.get("refresh_seconds", 120) or 120)).start()

        # A config that exists but will not parse falls back to demo numbers,
        # which look exactly like a working app pointed at an empty vault.
        if self._config_error:
            rumps.notification(
                t("notify_title"), "", t("config_broken", err=self._config_error))

        # Ask after the UI is up, so the first thing on screen is the chick
        # rather than a dialog from an app they have not seen yet.
        if self._first_run:
            rumps.Timer(self._offer_setup, 1.2).start()

    def _offer_setup(self, timer):
        timer.stop()
        try:
            self.first_run_setup()
            self.refresh_widget(None)
        except Exception:
            import traceback
            traceback.print_exc()

    # --- setup helpers ---

    def install_hotkeys(self, keys):
        try:
            self.hotkeys = HotKeys()
        except Exception as e:
            print(f"hotkeys unavailable: {e}", flush=True)
            self.hotkeys = None

        taken = []
        for name, fn in (("note", self.quick_note),
                         ("island", self._hk_island),
                         ("ball", self._hk_ball)):
            spec = keys.get(name)
            if not spec:
                continue
            try:
                ok = self.hotkeys and self.hotkeys.register_spec(spec, fn)
            except Exception as e:
                ok = False
                print(f"hotkey error {name}: {e}", flush=True)
            if ok:
                taken.append(describe(spec))
            else:
                print(f"hotkey busy or failed: {name} ({spec})", flush=True)
        self._hotkey_list = " / ".join(taken)
        if taken:
            print("hotkeys: " + self._hotkey_list, flush=True)
        if not trusted():
            print("hotkeys need Accessibility — see the menu", flush=True)

    @staticmethod
    def file_stamp():
        try:
            return config.SHELF_FILE.stat().st_mtime
        except OSError:
            return 0

    # --- shelf plumbing ---

    def commit(self):
        """Persist, then absorb our own write so the watcher stays quiet."""
        save_shelf(self.items)
        self._stamp = self.file_stamp()
        self.rebuild()

    def poll_file(self, _):
        stamp = self.file_stamp()
        if stamp != self._stamp:
            self._stamp = stamp
            self.items = load_shelf()
            self.rebuild()

    def _shelf_then_refresh(self, text):
        """Enter: park it on the shelf, decide later.

        The shelf is deliberately not the vault. Half of what you grab in a
        hurry turns out not to be worth keeping, and a vault that collects
        everything stops being a library.
        """
        r = add_to_shelf(text)
        self.after_capture()
        return r

    def _send_then_refresh(self, text):
        """Shift-Enter: send it where the notes live, skipping the shelf."""
        provider = self.cfg.get("provider")
        if provider == "http":
            from providers import http
            r = http.capture(self.cfg, text)
        elif provider == "folder":
            # Reading someone's vault and then saving their thoughts
            # somewhere else builds a second inbox — the exact failure this
            # app exists to notice.
            from providers import folder
            r = folder.capture(self.cfg, text)
        else:
            # Demo has nowhere to put it, so the shelf is the only honest
            # destination. Say so rather than pretending it went somewhere.
            r = add_to_shelf(text)
        self.after_capture()
        return r

    def after_capture(self):
        """Repaint shortly after a save so the numbers never show a state
        that the save already changed."""
        self.items = load_shelf()
        self._stamp = self.file_stamp()
        self.rebuild()
        bird = getattr(self, "bird", None)
        if bird is not None:
            bird.flap()
        rumps.Timer(self._repaint_once, 2).start()

    def _repaint_once(self, timer):
        timer.stop()
        data = self.fetch()
        if not data:
            return
        # Render only what is on screen, but the mood is read from the data
        # either way: the menu bar bird is visible whether or not the panel
        # is, and a hidden panel is no reason for it to stop telling you.
        if self.widget.visible():
            self.widget.render(data)
        self.sync_bird(data)

    def _start_bird(self, timer):
        timer.stop()
        try:
            item = self._nsapp.nsstatusitem
        except AttributeError:
            return
        self.bird = menubar.MenuBarBird(item, self._bird_icon)
        self.bird.start()
        self.sync_bird()

    def sync_bird(self, data=None):
        bird = getattr(self, "bird", None)
        if bird is None:
            return
        if data is not None:
            bird.set_mood(widget.mood_for((data or {}).get("fedHoursAgo")))
        else:
            bird.set_mood(getattr(self.widget, "mood", "ok"))

    # --- polling ---

    def poll_trust(self, _):
        now = trusted()
        if now != self._trusted:
            self._trusted = now
            self.rebuild()
            if now:
                rumps.notification(
                    t("notify_title"), "",
                    t("notify_hotkeys_live",
                      keys=getattr(self, "_hotkey_list", "")))

    def poll_cmd(self, _):
        """A command file, so external launchers can drive the app without
        needing a hotkey of their own."""
        try:
            if not config.CMD_FILE.exists():
                return
            cmd = config.CMD_FILE.read_text(encoding="utf-8").strip()
            config.CMD_FILE.unlink()
        except Exception:
            return
        try:
            if cmd == "island":
                self._hk_island()
            elif cmd == "ball":
                self._hk_ball()
            elif cmd == "card":
                self._ensure_visible()
                self.widget.unpark()
                self.widget.set_collapsed(False)
                self.rebuild()
            elif cmd == "note":
                self.quick_note()
            elif cmd == "toggle":
                if not self.widget.visible():
                    self.toggle_widget(None)
                else:
                    self.widget.toggle_collapsed()
            elif cmd == "show":
                self._ensure_visible()
            elif cmd == "pick":
                self.pick_folder()
        except Exception:
            import traceback
            traceback.print_exc()

    def refresh_widget(self, _):
        # This used to return early whenever the panel was hidden, which is
        # most of the time — and the menu bar bird would then be reporting a
        # mood from whenever you last opened the panel. Fetch either way on
        # the configured cadence; only the drawing is conditional.
        data = self.fetch()
        if not data:
            return
        self.sync_bird(data)
        if not self.widget.visible():
            return
        # Never redraw while they are typing — losing a half-written thought
        # is exactly the interruption this is meant to prevent.
        if (self.widget.field is not None
                and self.widget.field.stringValue().strip()):
            return
        self.widget.render(data)

    # --- forms ---

    def _ensure_visible(self):
        if not self.widget.visible():
            self.toggle_widget(None)

    def toggle_widget(self, _=None):
        # rumps swallows exceptions raised inside a menu callback, so a
        # failure here would look exactly like nothing happening.
        try:
            if self.widget.visible():
                self.widget.hide()
            else:
                data = self.fetch()
                if not data:
                    rumps.notification(t("notify_title"), "",
                                       t("notify_no_backend"))
                    return
                self.widget.render(data)
                self.widget.show()
            self.rebuild()
        except Exception as e:
            import traceback
            traceback.print_exc()
            rumps.notification(t("notify_title"),
                               t("notify_widget_failed"), str(e)[:80])

    def _hk_island(self):
        self._ensure_visible()
        self.widget.to_island()
        self.rebuild()

    def _hk_ball(self):
        self._ensure_visible()
        self.widget.unpark()
        self.widget.set_collapsed(True)
        self.rebuild()

    def quick_note(self, _=None):
        self._ensure_visible()
        self.widget.unpark()
        self.widget.set_collapsed(False)
        self.widget.focus_input()

    # --- setup ------------------------------------------------------------

    @objc.python_method
    def choose_folder(self, prompt=None):
        """Ask for a folder with the system panel.

        The alternative is telling someone to edit JSON inside ~/.config — a
        hidden directory Finder will not even show without a keystroke. That
        is a developer habit, and this is a notes app.
        """
        panel = AppKit.NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(False)
        panel.setPrompt_(t("pick_prompt"))
        panel.setMessage_(prompt or t("pick_message"))
        # An accessory app has no windows of its own to bring forward, so the
        # panel would otherwise open behind whatever you were looking at.
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        if panel.runModal() != AppKit.NSModalResponseOK:
            return None
        url = panel.URL()
        return url.path() if url else None

    def pick_folder(self, _=None):
        path = self.choose_folder()
        if not path:
            return
        config.save({"provider": "folder", "folder": {"path": path}})
        self.cfg = config.load()
        # The provider was bound at launch from the old config; without this
        # the picker would change the file and nothing on screen.
        self.fetch = providers.get(self.cfg)
        self.refresh_widget(None)
        # Say what was found, because a number appearing silently in a corner
        # is not an answer to "did that work".
        data = (self.fetch() if self.fetch else {}) or {}
        ready = (data.get("ready") or {}).get("count", 0)
        lib = data.get("library", 0)
        rumps.notification(
            t("notify_title"), "",
            t("pick_done", ready=ready, library=lib, path=path))

    @objc.python_method
    def first_run_setup(self):
        """On a genuinely first launch, offer to point at a folder straight
        away. Skipping is fine — demo data still runs — but the offer has to
        come before the user concludes the sample numbers are all there is."""
        win = rumps.Window(
            title=t("first_title"),
            message=t("first_message"),
            ok=t("first_ok"),
            cancel=t("first_skip"),
            dimensions=(0, 0),
        )
        if not win.run().clicked:
            config.save({})          # stop asking on every launch
            return
        path = self.choose_folder(t("pick_message"))
        if path:
            config.save({"provider": "folder", "folder": {"path": path}})
        else:
            config.save({})
        self.cfg = config.load()
        self.fetch = providers.get(self.cfg)

    # --- menu ---

    def rebuild(self):
        n = len(self.items)
        header = rumps.MenuItem(t("menu_header"))
        header.set_callback(None)
        # The real bird rather than the emoji stand-in: this line is the
        # closest thing the app has to an About box.
        _chick = widget._res("chick-18")
        if _chick:
            header.set_icon(_chick, dimensions=(16, 16))
        entries = [
            header,
            None,
            rumps.MenuItem(t("menu_note", key=self.note_key),
                           callback=self.quick_note),
            rumps.MenuItem(t("menu_clipboard"), callback=self.grab_clipboard),
            None,
            rumps.MenuItem(
                t("menu_widget_off") if (self.widget and self.widget.visible())
                else t("menu_widget_on"),
                callback=self.toggle_widget),
            rumps.MenuItem(
                t("menu_shelf_n", n=n) if n else t("menu_shelf"),
                callback=self.open_shelf),
            rumps.MenuItem(t("menu_open"), callback=self.open_dashboard),
            None,
            rumps.MenuItem(t("menu_pick_folder"), callback=self.pick_folder),
            *([] if self._trusted
              else [rumps.MenuItem(t("menu_ax"), callback=self.open_ax)]),
            rumps.MenuItem(t("menu_quit"), callback=rumps.quit_application),
        ]
        self.menu.clear()
        self.menu = entries
        # Stay narrow: a wide title is the first thing a crowded menu bar
        # pushes behind the overflow chevron.
        self.title = "" if not n else f" {n}"

    # --- actions ---

    def grab_clipboard(self, _=None):
        text = subprocess.run(["pbpaste"], capture_output=True,
                              text=True).stdout.strip()
        if not text:
            rumps.notification(t("notify_title"), "", t("notify_clip_empty"))
            return
        if any(i.get("text") == text for i in self.items):
            rumps.notification(t("notify_title"), "", t("notify_on_shelf"))
            return
        self.items.insert(0, {
            "text": text,
            "at": datetime.now().isoformat(timespec="seconds"),
        })
        del self.items[MAX_ITEMS:]
        self.commit()
        rumps.notification(t("notify_title"), "", t("notify_shelved"))

    def open_shelf(self, _=None):
        """No backend means no web UI, so fall back to the raw file — it is
        plain JSON and opening it beats a dead end."""
        url = self._dashboard_url("#shelf")
        if url:
            subprocess.run(["open", url])
        else:
            config.ensure_state_dir()
            if not config.SHELF_FILE.exists():
                save_shelf(self.items)
            subprocess.run(["open", str(config.SHELF_FILE)])

    def _dashboard_url(self, route=None):
        if self.cfg.get("provider") != "http":
            return ""
        from providers import http
        base = http.base_url(self.cfg)
        if not base:
            return ""
        if route:
            return base + "/" + route.lstrip("/")
        return http.open_url(self.cfg)

    def open_dashboard(self, route="#today"):
        url = self._dashboard_url(
            route if isinstance(route, str) and route.startswith("#") else None)
        if url:
            subprocess.run(["open", url])

    def open_ax(self, _=None):
        """Global key monitoring needs Accessibility; send them to the exact
        pane rather than describing where it is."""
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security"
            "?Privacy_Accessibility"])
        rumps.notification(t("notify_title"), t("menu_ax"),
                           t("notify_ax_hint"))


def main():
    # Deliberately does NOT write a default config here. Doing so made the
    # file exist before the app could ask whether this was a first run, so
    # the setup offer never appeared — the file is written once the user has
    # either chosen a folder or declined.
    config.ensure_state_dir()
    print("瞭望鸡 / Lookout Chicken starting", flush=True)
    ChickenApp().run()


if __name__ == "__main__":
    main()
