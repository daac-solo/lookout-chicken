"""
The widget — the ambient forcing function, in three forms.

It shows one thing above all: how long finished work has been sitting
unpublished. That number only does its job if you bump into it without
looking for it, which a browser tab can never manage.

Deliberately not a queue counter. An unread library is not a debt, so the
library line stays quiet and grey while the shipping lines carry the weight.

Three forms, each reachable directly by hotkey so none of them requires
clicking through another:
  card    a panel with a capture field and the full readout
  island  a pill flush under the notch, saying one short thing
  ball    a small draggable chick that idles with a breathing animation
"""

import random
from urllib.parse import quote

import AppKit
import objc

# CoreAnimation corner masks live in Quartz, not AppKit.
try:
    from Quartz import (kCALayerMaxXMaxYCorner, kCALayerMaxXMinYCorner,
                        kCALayerMinXMaxYCorner, kCALayerMinXMinYCorner)
    BOTTOM_CORNERS = kCALayerMinXMinYCorner | kCALayerMaxXMinYCorner
    ALL_CORNERS = (kCALayerMinXMinYCorner | kCALayerMaxXMinYCorner
                   | kCALayerMinXMaxYCorner | kCALayerMaxXMaxYCorner)
except ImportError:
    BOTTOM_CORNERS = 1 | 2
    ALL_CORNERS = 1 | 2 | 4 | 8
from Foundation import NSMakeRect, NSObject

import strings
from popup import Popup
from strings import t

W = 248
PAD = 14
INPUT_H = 46
PET = 72          # collapsed size
ISLAND_H = 30     # resting pill height

# Set from config at startup.
TYPE_SOUND = True
HINT_KEY = "⌃⌘N"


def configure(ui, note_key):
    """Apply the bits of config the widget cares about."""
    global TYPE_SOUND, HINT_KEY
    TYPE_SOUND = bool((ui or {}).get("type_sound", True))
    HINT_KEY = note_key or HINT_KEY


# One warm palette for the whole thing. The input was already paper; the
# rest was still system grey, which read as two unrelated objects stuck
# together.
def _c(r, g, b, a=1.0):
    return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


PAPER = _c(0.976, 0.961, 0.933, 0.93)
PAPER_SOLID = _c(0.976, 0.961, 0.933)
INK = _c(0.141, 0.125, 0.102)
DIM = _c(0.400, 0.376, 0.337)
FAINT = _c(0.580, 0.549, 0.494)
ALERT = _c(0.769, 0.322, 0.165)      # terracotta, not a siren red
CALM = _c(0.361, 0.478, 0.361)
GOLD = _c(0.769, 0.659, 0.510)

# The notch is pure black; the pill has to match it exactly or the seam shows.
NOTCH_BLACK = _c(0.0, 0.0, 0.0)
ISLAND_INK = _c(0.93, 0.92, 0.90)
ISLAND_ALERT = _c(0.98, 0.55, 0.38)


def _round(size, weight=AppKit.NSFontWeightRegular):
    """Rounded everywhere it can be: SF Rounded carries the Latin and the
    digits, Yuanti the Chinese. A warm interface should not be set in the
    same grotesque as a system alert."""
    base = AppKit.NSFont.systemFontOfSize_weight_(size, weight)
    try:
        d = base.fontDescriptor().fontDescriptorWithDesign_("rounded")
        if d:
            base = AppKit.NSFont.fontWithDescriptor_size_(d, size) or base
    except Exception:
        pass
    return base


def _round_cjk(size):
    return (AppKit.NSFont.fontWithName_size_("Yuanti SC", size)
            or _round(size))


def notched_screen():
    """mainScreen() follows the focused window, so on a two-display setup it
    wanders onto the external monitor that has no notch."""
    for sc in AppKit.NSScreen.screens():
        try:
            if sc.safeAreaInsets().top > 0:
                return sc
        except Exception:
            pass
    return AppKit.NSScreen.mainScreen()


def _label(text, size, color, weight=AppKit.NSFontWeightRegular, serif=False):
    f = AppKit.NSTextField.labelWithString_(text)
    if serif:
        f.setFont_(_round_cjk(size))
    else:
        f.setFont_(_round(size, weight))
    f.setTextColor_(color)
    f.setBackgroundColor_(AppKit.NSColor.clearColor())
    return f


def _res(name, ext="png"):
    """Bundle resource, or None when running straight from source."""
    return AppKit.NSBundle.mainBundle().pathForResource_ofType_(name, ext)


class KeyPanel(AppKit.NSPanel):
    """Borderless panels refuse key status by default, which leaves any text
    field inside them untypable."""

    def canBecomeKeyWindow(self):
        return True


class Widget(NSObject):
    def initWithOpener_handlers_(self, opener, handlers):
        self = objc.super(Widget, self).init()
        if self is None:
            return None
        self.open_url = opener
        self.on_shelf = handlers["shelf"]
        self.on_flow = handlers["flow"]
        self.panel = None
        self.field = None
        self.note = None
        self.prompt = random.choice(strings.prompts())
        self.collapsed = False
        self.parked = False
        self.mode = "card"   # card | island | ball
        self.popup = Popup.alloc().initWithPalette_({
            "paper": PAPER_SOLID.colorWithAlphaComponent_(0.97),
            "gold": GOLD,
            "font": lambda sz, bold: _round_cjk(sz) if bold else _round(sz),
        })
        self._dwell = None
        self._leave = None
        self.glass = False
        self.targets = []   # (y_low, y_high, route)
        self.last_data = None
        return self

    # --- window ---

    @objc.python_method
    def build(self):
        screen = AppKit.NSScreen.mainScreen()
        vf = screen.visibleFrame()
        # Top-right of the desktop, clear of the menu bar.
        x = vf.origin.x + vf.size.width - W - 24
        y = vf.origin.y + vf.size.height - 220

        panel = KeyPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, W, 200),
            AppKit.NSWindowStyleMaskBorderless
            | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered, False)
        # Float just under the status bar: high enough that it is actually
        # seen every day (a desktop-level panel is hidden the moment any
        # window covers it, which defeats the whole point), low enough that
        # it never steals focus or interrupts.
        panel.setLevel_(AppKit.NSFloatingWindowLevel)
        panel.setIgnoresMouseEvents_(False)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        # A small thing on a busy wallpaper disappears without a shadow.
        panel.setHasShadow_(True)
        panel.setMovableByWindowBackground_(True)
        panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle)

        # Liquid glass where the OS has it; the older blur otherwise.
        if hasattr(AppKit, "NSGlassEffectView"):
            blur = AppKit.NSGlassEffectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, W, 200))
            blur.setCornerRadius_(20)
            # Glass is the container, not the background. Text needs a ground
            # of its own, or a busy wallpaper reads straight through it.
            try:
                blur.setTintColor_(PAPER_SOLID.colorWithAlphaComponent_(0.72))
            except Exception:
                pass
            self.glass = True
        else:
            blur = AppKit.NSVisualEffectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, W, 200))
            blur.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
            blur.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
            blur.setState_(AppKit.NSVisualEffectStateActive)
            blur.setWantsLayer_(True)
            blur.layer().setCornerRadius_(14)
            blur.layer().setMasksToBounds_(True)
            blur.layer().setBackgroundColor_(PAPER.CGColor())
            self.glass = False
        panel.setContentView_(blur)

        sheet = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, 200))
        sheet.setWantsLayer_(True)
        sheet.layer().setBackgroundColor_(
            PAPER_SOLID.colorWithAlphaComponent_(0.90).CGColor())
        sheet.layer().setCornerRadius_(16)
        if hasattr(blur, "setContentView_"):
            blur.setContentView_(sheet)
        else:
            blur.addSubview_(sheet)

        stats = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, 200))
        sheet.addSubview_(stats)

        self.panel = panel
        self.body = blur
        self.sheet = sheet
        self.stats = stats

    @objc.python_method
    def show(self):
        if self.panel is None:
            self.build()
        self.panel.orderFront_(None)

    @objc.python_method
    def focus_input(self):
        """Take focus only when actually asked to type."""
        if self.panel and self.field:
            self.panel.makeKeyAndOrderFront_(None)
            self.panel.makeFirstResponder_(self.field)

    @objc.python_method
    def hide(self):
        if self.panel:
            self.panel.orderOut_(None)

    @objc.python_method
    def visible(self):
        return bool(self.panel and self.panel.isVisible())

    # --- forms ---

    @objc.python_method
    def set_collapsed(self, collapsed):
        """Collapsed, it is just a small thing sitting somewhere — present
        without asking for anything."""
        self.collapsed = collapsed
        self.mode = "ball" if collapsed else "card"
        if self.last_data is not None:
            self.render(self.last_data)

    @objc.python_method
    def island_line(self, data):
        """What the creature says. Ordered by what actually matters, phrased
        the way a person would mention it in passing — a system alert phrased
        as a system alert gets ignored by the second week."""
        d = (data or {}).get("distill") or {}
        r = (data or {}).get("ready") or {}
        sp = (data or {}).get("sparks") or {}
        shelf = (data or {}).get("shelf") or 0

        oldest = r.get("oldestDays") or 0
        if oldest >= 30:
            return t("island_oldest", n=oldest), True
        if r.get("count"):
            return t("island_ready", n=r["count"]), True
        if not d.get("done") and d.get("streak"):
            return t("island_streak", n=d["streak"]), True
        if sp.get("hot"):
            return t("island_sparks", n=sp["hot"]), False
        if shelf:
            return t("island_shelf", n=shelf), False
        if d.get("done"):
            return t("island_done"), False
        return t("island_clear"), False

    @objc.python_method
    def island_quiet(self, data):
        """Nothing pending: shrink to a bare chick. A strip that always says
        something is a strip you stop reading."""
        r = (data or {}).get("ready") or {}
        d = (data or {}).get("distill") or {}
        sp = (data or {}).get("sparks") or {}
        return not (r.get("count") or sp.get("hot")
                    or (data or {}).get("shelf") or not d.get("done"))

    @objc.python_method
    def render_island(self, data):
        for v in list(self.sheet.subviews()):
            v.removeFromSuperview()
        self.field = None

        # There are no pixels inside the cutout, so the island cannot be
        # drawn *in* the notch. Matching its black instead lets the eye read
        # the pill and the notch as one continuous shape.
        quiet = self.island_quiet(data)
        text, urgent = self.island_line(data)

        chick = None
        cp = _res("chick-18")
        if cp:
            chick = AppKit.NSImage.alloc().initWithContentsOfFile_(cp)

        label = _label("" if quiet else text, 12,
                       ISLAND_ALERT if urgent else ISLAND_INK,
                       AppKit.NSFontWeightMedium)
        label.sizeToFit()
        tw = label.frame().size.width
        w = 54 if quiet else min(max(tw + 56, 150), 380)

        screen = notched_screen()
        sf = screen.frame()
        try:
            notch = screen.safeAreaInsets().top
        except Exception:
            notch = 32

        # Flush against the bottom edge of the notch, centred on it: no gap
        # to read as a separate floating thing, no overlap to cover the bar.
        x = sf.origin.x + (sf.size.width - w) / 2
        y = sf.origin.y + sf.size.height - notch - ISLAND_H
        self.panel.setLevel_(AppKit.NSStatusWindowLevel + 1)
        self.panel.animator().setFrame_display_(
            NSMakeRect(x, y, w, ISLAND_H), True)

        if self.glass:
            self.body.setCornerRadius_(ISLAND_H / 2)
            try:
                self.body.setTintColor_(NOTCH_BLACK)
            except Exception:
                pass
        self.body.setWantsLayer_(True)
        self.body.layer().setCornerRadius_(ISLAND_H / 2)
        self.body.layer().setMasksToBounds_(True)
        self.body.layer().setBackgroundColor_(NOTCH_BLACK.CGColor())
        # Square the top corners so the pill reads as continuing out of the
        # notch rather than hanging beneath it.
        try:
            self.body.layer().setMaskedCorners_(BOTTOM_CORNERS)
        except Exception:
            pass
        self.body.setFrame_(NSMakeRect(0, 0, w, ISLAND_H))
        self.sheet.setFrame_(NSMakeRect(0, 0, w, ISLAND_H))
        self.sheet.layer().setBackgroundColor_(NOTCH_BLACK.CGColor())
        self.sheet.layer().setCornerRadius_(ISLAND_H / 2)
        self.sheet.layer().setBorderWidth_(0)
        try:
            self.sheet.layer().setMaskedCorners_(BOTTOM_CORNERS)
        except Exception:
            pass

        if chick is not None:
            iv = AppKit.NSImageView.alloc().initWithFrame_(
                NSMakeRect(16 if not quiet else (w - 18) / 2,
                           (ISLAND_H - 18) / 2, 18, 18))
            iv.setImage_(chick)
            iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
            self.sheet.addSubview_(iv)
            text_x = 42
        else:
            text_x = 16
        if not quiet:
            label.setFrame_(
                NSMakeRect(text_x, (ISLAND_H - 16) / 2, w - text_x - 14, 16))
            self.sheet.addSubview_(label)

        self._attach_pet_handlers()

    @objc.python_method
    def to_island(self):
        if self.panel is None:
            self.build()
        self.mode = "island"
        self.parked = True
        self.collapsed = True
        if self.last_data is not None:
            self.render(self.last_data)
        self.panel.orderFront_(None)

    @objc.python_method
    def unpark(self):
        """Back to an ordinary floating panel, clear of the menu bar."""
        if not getattr(self, "parked", False):
            return
        self.parked = False
        self.mode = "card"
        self.sheet.layer().setBackgroundColor_(
            PAPER_SOLID.colorWithAlphaComponent_(0.90).CGColor())
        self.sheet.layer().setCornerRadius_(16)
        if self.glass:
            try:
                self.body.setTintColor_(
                    PAPER_SOLID.colorWithAlphaComponent_(0.72))
                self.body.setCornerRadius_(20)
            except Exception:
                pass
        self.body.layer().setBackgroundColor_(
            AppKit.NSColor.clearColor().CGColor())
        for layer in (self.body.layer(), self.sheet.layer()):
            try:
                layer.setMaskedCorners_(ALL_CORNERS)
            except Exception:
                pass
        self.panel.setLevel_(AppKit.NSFloatingWindowLevel)
        screen = AppKit.NSScreen.mainScreen()
        vf = screen.visibleFrame()
        f = self.panel.frame()
        top = vf.origin.y + vf.size.height
        if f.origin.y + f.size.height > top:
            self.panel.setFrameOrigin_(
                AppKit.NSMakePoint(f.origin.x, top - f.size.height - 8))

    @objc.python_method
    def toggle_collapsed(self):
        # From the island, one tap opens the whole card.
        if self.mode == "island":
            self.mode = "card"
            self.unpark()
            self.set_collapsed(False)
            return
        if self.collapsed and getattr(self, "parked", False):
            self.unpark()
        self.set_collapsed(not self.collapsed)

    # --- motion ---

    @objc.python_method
    def breathe(self):
        """A barely-there idle loop. Perceptible as life, not as motion."""
        layer = self.sheet.layer()
        # Compare to None explicitly: truth-testing an ObjC object makes
        # PyObjC probe -length, which CABasicAnimation does not implement.
        if layer is None or layer.animationForKey_("breathe") is not None:
            return
        import Quartz
        a = Quartz.CABasicAnimation.animationWithKeyPath_("transform.scale")
        a.setFromValue_(1.0)
        a.setToValue_(1.015)
        a.setDuration_(1.6)
        a.setAutoreverses_(True)
        a.setRepeatCount_(1e9)
        a.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut"))
        # addAnimation:forKey: — animation first. Reversing these passes a
        # string where CoreAnimation wants an animation and crashes on
        # -[__NSCFString length] deep inside AppKit.
        layer.addAnimation_forKey_(a, "breathe")

    @objc.python_method
    def pulse(self, to=1.06, dur=0.16):
        """Reaction to something the user did — never spontaneous."""
        layer = self.sheet.layer()
        if layer is None:
            return
        import Quartz
        a = Quartz.CABasicAnimation.animationWithKeyPath_("transform.scale")
        a.setFromValue_(1.0)
        a.setToValue_(to)
        a.setDuration_(dur / 2)
        a.setAutoreverses_(True)
        a.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeOut"))
        layer.addAnimation_forKey_(a, "pulse")

    # --- ball ---

    @objc.python_method
    def _attach_pet_handlers(self):
        """Click to change form, hover to read. Shared by ball and island."""
        if not self.sheet.gestureRecognizers():
            click = AppKit.NSClickGestureRecognizer.alloc().initWithTarget_action_(
                self, "petClicked:")
            self.sheet.addGestureRecognizer_(click)

        # A tracking area so it can respond to the pointer — a thing that
        # never reacts reads as a picture, not a control.
        for ta in list(self.sheet.trackingAreas() or []):
            self.sheet.removeTrackingArea_(ta)
        area = AppKit.NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.sheet.bounds(),
            AppKit.NSTrackingMouseEnteredAndExited | AppKit.NSTrackingActiveAlways,
            self, None)
        self.sheet.addTrackingArea_(area)

    @objc.python_method
    def render_pet(self, data):
        for v in list(self.sheet.subviews()):
            v.removeFromSuperview()
        self.field = None

        r = (data or {}).get("ready") or {}
        overdue = (r.get("oldestDays") or 0) >= 30

        f = self.panel.frame()
        # Keep the top-left corner put so it does not jump when it shrinks.
        self.panel.setFrame_display_(
            NSMakeRect(f.origin.x, f.origin.y + f.size.height - PET,
                       PET, PET), True)
        self.body.setFrame_(NSMakeRect(0, 0, PET, PET))
        if self.glass:
            self.body.setCornerRadius_(PET / 2)
        else:
            self.body.layer().setCornerRadius_(PET / 2)
        self.sheet.setFrame_(NSMakeRect(0, 0, PET, PET))
        self.sheet.layer().setBackgroundColor_(
            PAPER_SOLID.colorWithAlphaComponent_(0.90).CGColor())
        self.sheet.layer().setCornerRadius_(PET / 2)
        self.sheet.layer().setBorderWidth_(1.5)
        self.sheet.layer().setBorderColor_(
            GOLD.colorWithAlphaComponent_(0.55).CGColor())
        try:
            self.sheet.layer().setMaskedCorners_(ALL_CORNERS)
        except Exception:
            pass

        self.breathe()
        # The real artwork when the bundle carries it; the emoji is only a
        # fallback for running straight from source.
        img = None
        path = _res("chick-72")
        if path:
            img = AppKit.NSImage.alloc().initWithContentsOfFile_(path)
        if img is not None:
            view = AppKit.NSImageView.alloc().initWithFrame_(
                NSMakeRect(7, 9, PET - 14, PET - 14))
            view.setImage_(img)
            view.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
            self.sheet.addSubview_(view)
        else:
            ball = AppKit.NSTextField.labelWithString_("🐔")
            ball.setFont_(AppKit.NSFont.systemFontOfSize_(26))
            ball.setAlignment_(AppKit.NSTextAlignmentCenter)
            ball.setFrame_(NSMakeRect(0, PET / 2 - 10, PET, 30))
            self.sheet.addSubview_(ball)

        n = r.get("count") or 0
        sub = AppKit.NSTextField.labelWithString_(str(n) if n else "")
        sub.setAlignment_(AppKit.NSTextAlignmentCenter)
        sub.setFont_(AppKit.NSFont.systemFontOfSize_weight_(
            10, AppKit.NSFontWeightSemibold))
        sub.setTextColor_(ALERT if overdue else FAINT)
        sub.setBackgroundColor_(AppKit.NSColor.clearColor())
        sub.setFrame_(NSMakeRect(0, 5, PET, 13))
        self.sheet.addSubview_(sub)

        self._attach_pet_handlers()

    # --- hover ---

    def mouseEntered_(self, _):
        # Wait for the cursor to actually rest. Without this gate, sweeping
        # past the notch fires the popup every time.
        if self._leave is not None:
            self._leave.invalidate()
            self._leave = None
        if self._dwell is not None:
            self._dwell.invalidate()
        self._dwell = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.12, False, lambda t: self.peek())

    def mouseExited_(self, _):
        if self._dwell is not None:
            self._dwell.invalidate()
            self._dwell = None
        if self._leave is not None:
            self._leave.invalidate()
        self._leave = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.25, False, lambda t: self.popup.hide())

    @objc.python_method
    def peek(self):
        """Hover shows; it never needs a click to be read."""
        self._dwell = None
        d = (self.last_data or {}).get("distill") or {}
        r = (self.last_data or {}).get("ready") or {}
        sp = (self.last_data or {}).get("sparks") or {}
        shelf = (self.last_data or {}).get("shelf") or 0
        lib = (self.last_data or {}).get("library") or 0

        lines = []
        oldest = r.get("oldestDays") or 0
        if r.get("count"):
            lines.append((t("ready_count", n=r["count"]), 13, INK, True))
            lines.append((t("oldest_days", n=oldest), 12,
                          ALERT if oldest >= 30 else DIM, False))
            for it in (r.get("items") or [])[:2]:
                lines.append(("· " + (it.get("title") or "")[:20],
                              11, FAINT, False))
        if d.get("todayDay"):
            lines.append((t("peek_distill", day=d["todayDay"],
                            n=d.get("streak", 0)),
                          12, CALM if d.get("done") else INK, False))
            lines.append((t("peek_today_done") if d.get("done")
                          else t("peek_today_todo"), 11,
                          FAINT if d.get("done") else ALERT, False))
        if sp.get("hot"):
            lines.append((t("sparks_hot", n=sp["hot"]), 11, DIM, False))
        tail = t("library", n=lib)
        if shelf:
            tail += t("shelf_suffix", n=shelf)
        lines.append((tail, 11, FAINT, False))
        lines.append((t("peek_hint", key=HINT_KEY), 10, FAINT, False))
        lines.append((t("peek_sig"), 9, GOLD, False))

        self.popup.show(lines, AppKit.NSEvent.mouseLocation())

    def petClicked_(self, _):
        self.toggle_collapsed()

    # --- card ---

    @objc.python_method
    def render(self, data):
        if self.panel is None:
            self.build()
        self.last_data = data
        if self.mode == "island":
            self.render_island(data)
            return
        if self.collapsed:
            self.render_pet(data)
            return

        self.keep_draft()
        if not self.glass:
            self.body.layer().setCornerRadius_(14)
        self.sheet.layer().setBackgroundColor_(
            PAPER_SOLID.colorWithAlphaComponent_(0.90).CGColor())
        self.sheet.layer().setCornerRadius_(16)
        self.sheet.layer().setBorderWidth_(0)

        # The ball and island own the whole sheet; coming back to the card
        # means rebuilding the stats container they tore down.
        for v in list(self.sheet.subviews()):
            v.removeFromSuperview()
        self.stats = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, W, 200))
        self.sheet.addSubview_(self.stats)
        for g in list(self.sheet.gestureRecognizers() or []):
            self.sheet.removeGestureRecognizer_(g)
        for ta in list(self.sheet.trackingAreas() or []):
            self.sheet.removeTrackingArea_(ta)

        label, second, tertiary = INK, DIM, FAINT
        red, green = ALERT, CALM

        lines = []  # (view, height, gap_after, route)

        d = data.get("distill") or {}
        if d:
            streak = d.get("streak", 0)
            done = d.get("done")
            lines.append((_label(t("distill_day", day=d.get("todayDay", "?")),
                                 11, second), 14, 2, "#today"))
            lines.append((
                _label(t("streak_done", n=streak) if done
                       else t("streak_todo", n=streak),
                       14, green if done else label,
                       AppKit.NSFontWeightSemibold, serif=True),
                19, 13, "#today"))

        r = data.get("ready") or {}
        n, oldest = r.get("count", 0), r.get("oldestDays", 0)
        if n:
            lines.append((_label(t("ready_count", n=n), 14, label,
                                 AppKit.NSFontWeightSemibold, serif=True),
                          19, 2, "#make"))
            # The whole widget exists for this line.
            lines.append((_label(t("oldest_days", n=oldest), 13,
                                 red if oldest >= 30 else second,
                                 serif=True), 18, 11, "#make"))
            for it in (r.get("items") or [])[:2]:
                title = (it.get("title") or "")[:22]
                # Straight to that piece, not a general list.
                lines.append((_label(f"· {title}", 11, tertiary), 14, 1,
                              "#publish=" + quote(str(it.get("id") or ""),
                                                  safe="")))
            if lines:
                a, b, _, rt = lines[-1]
                lines[-1] = (a, b, 12, rt)

        s = data.get("sparks") or {}
        if s.get("hot"):
            lines.append((_label(t("sparks_hot", n=s["hot"]), 12, second),
                          16, 3, "#make"))

        lib = data.get("library", 0)
        shelf = data.get("shelf", 0)
        tail = t("library", n=lib)
        if shelf:
            tail += t("shelf_suffix", n=shelf)
        lines.append((_label(tail, 11, tertiary), 14, 2, "#focus"))
        lines.append((_label(t("collapse"), 11, tertiary), 13, 0, "collapse"))

        total = PAD * 2 + INPUT_H + 12 + sum(h + g for _, h, g, _r in lines)
        f = self.panel.frame()
        # Grow downward from a fixed top edge so the widget never drifts.
        self.panel.setFrame_display_(
            NSMakeRect(f.origin.x, f.origin.y + f.size.height - total,
                       W, total), True)
        self.body.setFrame_(NSMakeRect(0, 0, W, total))
        self.sheet.setFrame_(NSMakeRect(0, 0, W, total))

        # A capture field that is always visible costs nothing to use. Having
        # to open something first is the interruption worth removing.
        field = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(PAD, total - PAD - INPUT_H, W - PAD * 2, INPUT_H))
        # A rounded face at reading size, on warm paper rather than system
        # grey: the field should feel like somewhere you write.
        field.setFont_(_round_cjk(15))
        field.setBezeled_(False)
        field.setDrawsBackground_(True)
        field.setBackgroundColor_(_c(0.995, 0.985, 0.962, 0.96))
        field.setFocusRingType_(AppKit.NSFocusRingTypeNone)
        field.setPlaceholderString_(self.prompt
                                    or random.choice(strings.prompts()))
        field.setTextColor_(INK)
        field.setDelegate_(self)
        try:
            field.setInsertionPointColor_(ALERT)
        except Exception:
            pass
        field.setWantsLayer_(True)
        field.layer().setCornerRadius_(9)
        field.layer().setBorderWidth_(1.0)
        field.layer().setBorderColor_(
            GOLD.colorWithAlphaComponent_(0.42).CGColor())
        field.setStringValue_(self.note or "")
        self.sheet.addSubview_(field)
        self.field = field
        self.stats.setFrame_(NSMakeRect(0, 0, W, total - PAD - INPUT_H - 6))

        y = self.stats.frame().size.height
        self.targets = []
        for view, h, gap, route in lines:
            y -= h
            view.setFrame_(NSMakeRect(PAD, y, W - PAD * 2, h))
            self.stats.addSubview_(view)
            # Generous hit band: these lines are small and the pointer is not.
            self.targets.append((y - gap / 2, y + h + 2, route))
            y -= gap

        if not self.stats.gestureRecognizers():
            click = AppKit.NSClickGestureRecognizer.alloc().initWithTarget_action_(
                self, "clicked:")
            self.stats.addGestureRecognizer_(click)

    def clicked_(self, _):
        loc = self.stats.gestureRecognizers()[0].locationInView_(self.stats)
        route = "#today"
        for low, high, r in self.targets:
            if low <= loc.y <= high:
                route = r
                break
        if route == "collapse":
            self.toggle_collapsed()
        else:
            self.open_url(route)

    # --- typing ---

    def controlTextDidChange_(self, note):
        self.tick()

    @objc.python_method
    def tick(self):
        """A soft key sound. Quiet enough to live with, present enough that
        writing here feels like writing somewhere."""
        if not TYPE_SOUND:
            return
        snd = AppKit.NSSound.soundNamed_("Morse")
        if snd:
            snd.setVolume_(0.045)
            snd.stop()
            snd.play()

    # Enter files the thought and clears the field; nothing else moves, no
    # window opens, and whatever you were doing stays where it was.
    def control_textView_doCommandBySelector_(self, control, view, selector):
        name = selector.name() if hasattr(selector, "name") else str(selector)

        if name == "cancelOperation:":
            self.field.setStringValue_("")
            self.note = ""
            self.panel.makeFirstResponder_(None)
            return True

        if name == "insertNewline:":
            text = self.field.stringValue().strip()
            if not text:
                return True
            shift = (AppKit.NSEvent.modifierFlags()
                     & AppKit.NSEventModifierFlagShift) != 0
            ok, info = (self.on_flow(text) if shift else self.on_shelf(text))
            self.field.setStringValue_("")
            self.note = ""
            # A fresh invitation each time, so the next thought meets a
            # slightly different door.
            self.prompt = random.choice(strings.prompts())
            if ok:
                if TYPE_SOUND:
                    snd = AppKit.NSSound.soundNamed_("Bottle")
                    if snd:
                        snd.setVolume_(0.10)
                        snd.play()
                self.pulse()
            self.flash(t("capture_ok") if ok else t("capture_fail", err=info),
                       ok)
            return True

        return False

    @objc.python_method
    def flash(self, text, good):
        """Confirm in place — a notification would be another interruption."""
        self.field.setPlaceholderString_(text)
        AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            1.6, False,
            lambda tm: self.field and self.field.setPlaceholderString_(
                self.prompt))

    @objc.python_method
    def keep_draft(self):
        """Survive a re-render mid-sentence."""
        if self.field:
            self.note = self.field.stringValue()
