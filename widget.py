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

import os
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
# Loud enough to feel the key, quiet enough to type next to someone.
KEY_VOLUME = 0.30
ERROR_LOG = os.path.join(os.path.expanduser("~"),
                         ".local", "share", "lookout-chicken", "error.log")
# Generated on first use into app state, not shipped as a binary asset:
# the character is tuned by reading numbers in keysound.py rather than by
# opening an audio editor.
KEY_DIR = os.path.join(os.path.expanduser("~"),
                       ".local", "share", "lookout-chicken", "keys")
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
# Grain, not gold. GOLD on paper measures 2.1:1 — technically drawn, and in
# practice a dot nobody can see.
GRAIN = _c(0.56, 0.40, 0.20)
# Said once, after the last grain.
YUMS = ["yummy", "好吃", "yum yum", "再来点", "😋", "咕咕"]

# How long since anything went into the system. The companion wears this:
# fed and lively, settled, hungry, or droopy. It is the one state it has that
# the user can actually change, which is what makes feeding it mean something.
MOODS = [
    (0.5,  "fed"),
    (6.0,  "ok"),
    (24.0, "hungry"),
    (1e9,  "droopy"),
]


def mood_for(hours):
    """Providers that cannot tell how stale the data is simply omit the
    field; a neutral mood is better than inventing neglect."""
    if hours is None:
        return "ok"
    for limit, name in MOODS:
        if hours < limit:
            return name
    return "droopy"

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


def _text_width(text, size):
    """Measure rather than guess: CJK and Latin differ enough at 11pt that a
    fixed per-character width would leave chips either clipped or padded."""
    try:
        attrs = {AppKit.NSFontAttributeName: _round_cjk(size)}
        return float(AppKit.NSString.stringWithString_(text)
                     .sizeWithAttributes_(attrs).width)
    except Exception:
        return 11.0 * len(text)


def _label(text, size, color, weight=AppKit.NSFontWeightRegular, serif=False):
    f = AppKit.NSTextField.labelWithString_(text)
    if serif:
        f.setFont_(_round_cjk(size))
    else:
        f.setFont_(_round(size, weight))
    f.setTextColor_(color)
    f.setBackgroundColor_(AppKit.NSColor.clearColor())
    return f


_LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo")


def _res(name, ext="png"):
    """The artwork, from the bundle when there is one and from the repo's
    logo/ folder when running straight from source.

    Without the source fallback the chick silently degrades to an emoji
    before the first build, which reads as "this is what it looks like"
    rather than "the bundle is missing".
    """
    path = AppKit.NSBundle.mainBundle().pathForResource_ofType_(name, ext)
    if path:
        return path
    local = os.path.join(_LOGO_DIR, f"{name}.{ext}")
    return local if os.path.exists(local) else None


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
        self.on_pick = handlers.get("pick")
        # Loaded once: building an NSSound per keystroke would stutter.
        self._keys = []
        self._key_i = 0
        self._grains_snd = []
        self._grain_i = 0
        try:
            import keysound
            for path in keysound.ensure_grain(KEY_DIR):
                snd = AppKit.NSSound.alloc().initWithContentsOfFile_byReference_(
                    path, True)
                if snd is not None:
                    self._grains_snd.append(snd)
        except Exception:
            pass
        try:
            import keysound
            for path in keysound.ensure(KEY_DIR):
                snd = AppKit.NSSound.alloc().initWithContentsOfFile_byReference_(
                    path, True)
                if snd is not None:
                    self._keys.append(snd)
        except Exception as e:
            print(f"key sound unavailable: {e}", flush=True)
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
        self.mood = "ok"
        self.card_chick = None
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
        # Tracking areas on a panel that never becomes key get no enter or
        # exit events while the app is in the background. This does not fix
        # that on its own — see start_hover_watch — but without it even the
        # cases that could work do not.
        panel.setAcceptsMouseMovedEvents_(True)
        panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle)

        # Liquid glass where the OS has it; the older blur otherwise.
        if hasattr(AppKit, "NSGlassEffectView"):
            blur = AppKit.NSGlassEffectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, W, 200))
            blur.setCornerRadius_(20)
            blur.setWantsLayer_(True)
            # Without the mask, a child layer's square corner paints past the
            # rounded glass edge.
            blur.layer().setMasksToBounds_(True)
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
        # A borderless window keeps the shadow outline of its previous frame.
        # Without this the old square corners stay painted outside the pill.
        self.panel.invalidateShadow()

        self._attach_pet_handlers()
        self.panel.invalidateShadow()

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
        """The ball's own breath. Shares the curve the card uses so both read
        as the same creature: a long inhale, a held top, a slower release."""
        layer = self.sheet.layer()
        # Compare to None explicitly: truth-testing an ObjC object makes
        # PyObjC probe -length, which CABasicAnimation does not implement.
        if layer is None or layer.animationForKey_("breathe") is not None:
            return
        import Quartz
        layer.setAnchorPoint_(AppKit.NSMakePoint(0.5, 0.42))
        scale = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.scale")
        scale.setValues_([1.0, 1.055, 1.045, 1.0, 1.0])
        scale.setKeyTimes_([0, 0.30, 0.46, 0.80, 1.0])
        ease = Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut")
        scale.setTimingFunctions_([ease, ease, ease, ease])
        scale.setDuration_(2.6)
        scale.setRepeatCount_(1e9)
        # addAnimation:forKey: — animation first. Reversing these passes a
        # string where CoreAnimation wants an animation and crashes on
        # -[__NSCFString length] deep inside AppKit.
        layer.addAnimation_forKey_(scale, "breathe")

    @objc.python_method
    def breathe_view(self, view):
        """The card's breath. The whole surface rises and settles; a lone
        corner glyph pulsing instead would read as a loading indicator."""
        layer = view.layer()
        if layer is None or layer.animationForKey_("breathe") is not None:
            return
        import Quartz
        # Anchored at the bottom edge, so it lifts off the desk rather than
        # swelling in both directions.
        layer.setAnchorPoint_(AppKit.NSMakePoint(0.5, 0.0))
        group = Quartz.CAAnimationGroup.animation()

        scale = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.scale")
        scale.setValues_([1.0, 1.012, 1.010, 1.0, 1.0])
        scale.setKeyTimes_([0, 0.30, 0.46, 0.80, 1.0])

        lift = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        lift.setValues_([0, -1.6, -1.3, 0, 0])
        lift.setKeyTimes_([0, 0.30, 0.46, 0.80, 1.0])

        ease = Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut")
        for a in (scale, lift):
            a.setTimingFunctions_([ease, ease, ease, ease])

        group.setAnimations_([scale, lift])
        group.setDuration_(2.6)
        group.setRepeatCount_(1e9)
        layer.addAnimation_forKey_(group, "breathe")

    @objc.python_method
    def chick_idle(self, view):
        """Posture carries the mood. Same bird, different tempo and tilt —
        cheaper and more legible than drawing four chickens."""
        layer = view.layer()
        if layer is None:
            return
        import Quartz
        layer.removeAnimationForKey_("mood")
        layer.setAnchorPoint_(AppKit.NSMakePoint(0.5, 0.0))

        period, bob, tilt, alpha = {
            # (period, bob px, tilt deg, opacity)
            "fed":    (0.62, 5.0, 7.0, 1.00),
            "ok":     (2.60, 1.8, 0.0, 1.00),
            "hungry": (3.40, 1.0, -5.0, 0.80),
            "droopy": (4.60, 0.5, -11.0, 0.58),
        }[self.mood]

        view.setAlphaValue_(alpha)

        bobA = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        bobA.setValues_([0, bob, bob * 0.8, 0, 0])
        bobA.setKeyTimes_([0, 0.30, 0.46, 0.80, 1.0])
        ease = Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut")
        bobA.setTimingFunctions_([ease, ease, ease, ease])

        rot = Quartz.CABasicAnimation.animationWithKeyPath_(
            "transform.rotation.z")
        rot.setFromValue_(tilt * 3.14159 / 180.0)
        rot.setToValue_(
            (tilt + (4 if self.mood == "fed" else 1.2)) * 3.14159 / 180.0)
        rot.setAutoreverses_(True)

        group = Quartz.CAAnimationGroup.animation()
        group.setAnimations_([bobA, rot])
        group.setDuration_(period)
        group.setRepeatCount_(1e9)
        layer.addAnimation_forKey_(group, "mood")

    @objc.python_method
    def feed(self):
        """Scatter rice to one side and let it walk over and eat.

        Pecking on the spot read as a twitch. The reward for putting
        something in should be a small story: grain lands over there, it
        notices, it goes, it eats, it comes back. Nothing else in the app
        moves across the surface, which is what makes this worth watching.
        """
        view = getattr(self, "card_chick", None)
        if view is None or view.layer() is None:
            return
        import Quartz

        now = Quartz.CACurrentMediaTime()
        f = view.frame()
        n = 4
        # The grain lands to its left, on the same line it stands on, with a
        # gap wide enough that walking there is visibly a journey.
        gx0 = f.origin.x - 74
        spacing = 15
        ground = f.origin.y + 4
        drop_from = f.size.height + 26

        FALL = 0.34          # grain in the air
        STAGGER = 0.14       # one at a time, not a handful at once
        WALK = 0.42          # getting there
        PECK = 0.30          # one grain
        # It sets off as the last grain lands, not before: a bird that starts
        # walking toward food still in the air is not reacting to anything.
        start_walk = (n - 1) * STAGGER + FALL - 0.06
        start_peck = start_walk + WALK
        eat = n * PECK
        back_at = start_peck + eat

        grains = []
        for i in range(n):
            # Bigger and oval: a circle at this size is a speck, a grain has
            # a long axis you can actually recognise.
            g = AppKit.NSView.alloc().initWithFrame_(
                NSMakeRect(gx0 + i * spacing, ground, 6.0, 4.0))
            g.setWantsLayer_(True)
            g.layer().setCornerRadius_(2.0)
            g.layer().setBackgroundColor_(GRAIN.CGColor())
            # A hairline of shadow so it sits ON the paper rather than in it.
            g.layer().setShadowColor_(INK.CGColor())
            g.layer().setShadowOpacity_(0.22)
            g.layer().setShadowRadius_(1.0)
            g.layer().setShadowOffset_(AppKit.NSMakeSize(0, -0.5))
            self.sheet.addSubview_(g)
            grains.append(g)

            fall = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
                "transform.translation.y")
            # A small bounce where it lands, so the grain has weight.
            fall.setValues_([drop_from, 0, 5, 0])
            fall.setKeyTimes_([0, 0.82, 0.92, 1.0])
            fall.setDuration_(FALL)
            fall.setBeginTime_(now + i * STAGGER)
            fall.setTimingFunction_(
                Quartz.CAMediaTimingFunction.functionWithName_("easeIn"))
            fall.setFillMode_("backwards")
            g.layer().addAnimation_forKey_(fall, "fall")

            # A tick as each one lands. Quiet: four in a second, and the
            # point is texture rather than punctuation.
            AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                i * STAGGER + FALL * 0.86, False,
                lambda t: self._grain_tick())

            # Eaten in the order it walks past them, one per peck.
            AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                start_peck + (i + 0.55) * PECK, False,
                lambda t, gg=g: gg.removeFromSuperview())

        # --- the walk: two hops out, eat, two hops back ---
        dx = (gx0 + (n - 1) * spacing / 2.0) - (f.origin.x + f.size.width / 2.0)
        total = back_at + WALK

        def at(t):
            return max(0.0, min(1.0, t / total))

        move = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.x")
        move.setValues_([0, 0, dx, dx, 0])
        move.setKeyTimes_([0, at(start_walk), at(start_peck),
                           at(back_at), 1.0])
        move.setTimingFunctions_([
            Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut")] * 4)

        # Hops rather than a glide: a bird that slides looks like a cursor.
        hop_v, hop_t = [0], [0.0]
        for seg_start, seg_len, hops in ((start_walk, WALK, 2),
                                         (back_at, WALK, 2)):
            for h in range(hops):
                a = seg_start + seg_len * (h + 0.5) / hops
                b = seg_start + seg_len * (h + 1.0) / hops
                hop_v += [7, 0]
                hop_t += [at(a), at(b)]
        # The last hop already lands on 1.0; appending another would give
        # CoreAnimation two keyframes at the same time, which it renders as
        # a stutter at the end of the walk.
        if hop_t[-1] < 1.0:
            hop_v.append(0)
            hop_t.append(1.0)
        jump = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        jump.setValues_(hop_v)
        jump.setKeyTimes_(hop_t)

        # One dip of the head per grain, while it is standing over them.
        d = 3.14159 / 180.0
        pv, pt = [0], [0.0]
        for i in range(n):
            a = start_peck + (i + 0.25) * PECK
            b = start_peck + (i + 0.70) * PECK
            pv += [22 * d, 0]
            pt += [at(a), at(b)]
        if pt[-1] < 1.0:
            pv.append(0)
            pt.append(1.0)
        peck = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.rotation.z")
        peck.setValues_(pv)
        peck.setKeyTimes_(pt)

        # Children of a group do NOT inherit its duration. Left at 0 they
        # each run for CoreAnimation's default 0.25s and snap back, which
        # looks exactly like the chick never moving at all.
        for a in (move, jump, peck):
            a.setDuration_(total)

        group = Quartz.CAAnimationGroup.animation()
        group.setAnimations_([move, jump, peck])
        group.setDuration_(total)
        group.setRemovedOnCompletion_(True)
        layer = view.layer()
        # Drop the idle loop for the duration, or the two fight over the
        # same transform and the walk comes out jittery.
        layer.removeAnimationForKey_("mood")
        layer.addAnimation_forKey_(group, "feed")

        # A word of thanks once the last grain is gone — the point of the
        # whole animation is that putting something in felt worth doing.
        AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            back_at - 0.05, False, lambda t: self._yum(view))

        self.mood = "fed"
        AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            total + 0.05, False, lambda t: self.chick_idle(view))

    @objc.python_method
    def _grain_tick(self):
        if not TYPE_SOUND or not self._grains_snd:
            return
        self._grain_i = (self._grain_i + 1) % len(self._grains_snd)
        snd = self._grains_snd[self._grain_i]
        snd.setVolume_(0.16)
        snd.stop()
        snd.play()

    @objc.python_method
    def _yum(self, view):
        """A small label that floats up off the chick and fades."""
        if self.sheet is None or view is None:
            return
        import Quartz
        f = view.frame()
        word = random.choice(YUMS)
        label = _label(word, 12, GRAIN, AppKit.NSFontWeightSemibold)
        w = _text_width(word, 12) + 4
        # Centred over wherever it is standing, which is away from home.
        dx = 0.0
        try:
            t = view.layer().presentationLayer()
            if t is not None:
                dx = t.transform().m41 if hasattr(t.transform(), "m41") else 0.0
        except Exception:
            dx = 0.0
        label.setFrame_(NSMakeRect(f.origin.x + dx + (f.size.width - w) / 2.0,
                                   f.origin.y + f.size.height - 2, w, 16))
        label.setAlphaValue_(0.0)
        # An NSTextField has no layer until asked, and a layerless view
        # silently ignores every animation added to it.
        label.setWantsLayer_(True)
        self.sheet.addSubview_(label)
        if label.layer() is None:
            label.setAlphaValue_(1.0)
            AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                0.9, False, lambda t: label.removeFromSuperview())
            return

        rise = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        rise.setValues_([0, 14, 20])
        rise.setKeyTimes_([0, 0.55, 1.0])
        fade = Quartz.CAKeyframeAnimation.animationWithKeyPath_("opacity")
        fade.setValues_([0.0, 1.0, 1.0, 0.0])
        fade.setKeyTimes_([0, 0.18, 0.62, 1.0])
        grp = Quartz.CAAnimationGroup.animation()
        grp.setAnimations_([rise, fade])
        grp.setDuration_(1.1)
        grp.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeOut"))
        label.layer().addAnimation_forKey_(grp, "yum")

        AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            1.15, False, lambda t: label.removeFromSuperview())

    @objc.python_method
    def chick_hello(self):
        """Hover: it notices you."""
        view = self.card_chick
        if view is None or view.layer() is None:
            return
        import Quartz
        d = 3.14159 / 180.0
        a = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.rotation.z")
        a.setValues_([0, -14 * d, 6 * d, -4 * d, 0])
        a.setDuration_(0.6)
        a.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeInEaseOut"))
        view.layer().addAnimation_forKey_(a, "hello")

    @objc.python_method
    def chick_poke(self):
        """Click: a startled hop."""
        view = self.card_chick
        if view is None or view.layer() is None:
            return
        import Quartz
        a = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        a.setValues_([0, 13, -3, 5, 0])
        a.setKeyTimes_([0, 0.26, 0.55, 0.78, 1.0])
        a.setDuration_(0.5)
        a.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeOut"))
        view.layer().addAnimation_forKey_(a, "poke")

    @objc.python_method
    def cheer(self):
        """React to what the user just did, never on its own schedule."""
        if self.sheet is None or self.sheet.layer() is None:
            return
        import Quartz
        hop = Quartz.CAKeyframeAnimation.animationWithKeyPath_(
            "transform.translation.y")
        hop.setValues_([0, 5, -1.5, 0])
        hop.setKeyTimes_([0, 0.35, 0.68, 1.0])
        hop.setDuration_(0.52)
        hop.setTimingFunction_(
            Quartz.CAMediaTimingFunction.functionWithName_("easeOut"))
        self.sheet.layer().addAnimation_forKey_(hop, "cheer")

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

        self.panel.invalidateShadow()

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

    def chickClicked_(self, _):
        self.chick_poke()

    def mouseEntered_(self, note):
        # The chick has a tracking area of its own; greet rather than popping
        # the info panel when the pointer is on the bird itself.
        try:
            info = note.userInfo()
            if info and info.get("chick"):
                self.chick_hello()
                return
        except Exception:
            pass
        self._mouse_entered_panel()

    # --- hover -----------------------------------------------------------
    # Tracking areas do not work here. This panel is a non-activating one, and
    # while the app is in the background macOS does not deliver mouse-moved
    # events to it at all — NSTrackingActiveAlways governs which areas are
    # eligible, not whether the window is sent anything to match against.
    # Clicks still arrive, which is why the chick reacted to a click and
    # ignored the pointer.
    #
    # NSEvent.mouseLocation() reads correctly from a background app, so the
    # hover is computed here instead. A timer that only runs while the panel
    # is on screen, comparing one point against two rectangles.

    @objc.python_method
    def start_hover_watch(self):
        if getattr(self, "_hover_timer", None) is not None:
            return
        self._in_panel = False
        self._in_chick = False
        self._hover_timer = (
            AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                0.12, True, lambda t: self._hover_tick()))

    @objc.python_method
    def stop_hover_watch(self):
        t = getattr(self, "_hover_timer", None)
        if t is not None:
            t.invalidate()
            self._hover_timer = None
        self._in_panel = False
        self._in_chick = False

    @objc.python_method
    def _screen_rect(self, view):
        try:
            r = view.convertRect_toView_(view.bounds(), None)
            return self.panel.convertRectToScreen_(r)
        except Exception:
            return None

    @objc.python_method
    def _hover_tick(self):
        if self.panel is None or not self.panel.isVisible():
            return
        p = AppKit.NSEvent.mouseLocation()
        pf = self.panel.frame()
        in_panel = (pf.origin.x <= p.x <= pf.origin.x + pf.size.width
                    and pf.origin.y <= p.y <= pf.origin.y + pf.size.height)

        chick = getattr(self, "card_chick", None)
        in_chick = False
        if chick is not None and in_panel:
            r = self._screen_rect(chick)
            if r is not None:
                # A little slack: a 36pt bird is a small target to hold.
                pad = 6
                in_chick = (r.origin.x - pad <= p.x <= r.origin.x + r.size.width + pad
                            and r.origin.y - pad <= p.y <= r.origin.y + r.size.height + pad)

        if in_chick and not self._in_chick:
            self.chick_hello()
        self._in_chick = in_chick

        if in_panel and not self._in_panel:
            self._mouse_entered_panel()
        elif not in_panel and self._in_panel:
            self.mouseExited_(None)
        self._in_panel = in_panel

    @objc.python_method
    def _mouse_entered_panel(self):
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
        """Hover shows; it never needs a click to be read. Expanded, the card
        already says all of this — repeating it on top is just noise."""
        self._dwell = None
        if self.mode == "card" and not self.collapsed:
            return
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
        self.mood = mood_for((data or {}).get("fedHoursAgo"))
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

        # Zero is ambiguous: a wrong path, a state name that does not match,
        # and notes without frontmatter all render as 0. Say which one it is
        # while the user can still act on it, rather than leaving them to
        # conclude the app does not work.
        if not n and data.get("source") == "folder":
            lines.append((_label(
                t("none_no_files") if not lib else t("none_no_states"),
                11, red if not lib else second), 15, 4, "pick"))

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

        # Recompute the window shadow against the new rounded shape.
        self.panel.invalidateShadow()

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

        # It keeps you company while the card is open, down in the corner
        # where it never covers a line you are reading.
        self.card_chick = None
        path = _res("chick-72")
        img = (AppKit.NSImage.alloc().initWithContentsOfFile_(path)
               if path else None)
        if img is not None:
            side = 36
            iv = AppKit.NSImageView.alloc().initWithFrame_(
                NSMakeRect(W - side - 13, 11, side, side))
            iv.setImage_(img)
            iv.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
            iv.setWantsLayer_(True)
            self.sheet.addSubview_(iv)
            self.card_chick = iv
            self.chick_idle(iv)

            # Its own tracking area, tagged so mouseEntered: can tell the
            # bird apart from the rest of the card.
            for ta in list(iv.trackingAreas() or []):
                iv.removeTrackingArea_(ta)
            iv.addTrackingArea_(
                AppKit.NSTrackingArea.alloc()
                .initWithRect_options_owner_userInfo_(
                    iv.bounds(),
                    AppKit.NSTrackingMouseEnteredAndExited
                    | AppKit.NSTrackingActiveAlways,
                    self, {"chick": True}))
            iv.addGestureRecognizer_(
                AppKit.NSClickGestureRecognizer.alloc()
                .initWithTarget_action_(self, "chickClicked:"))

        # The card itself breathes, not the bird in it.
        self.breathe_view(self.sheet)

    def clicked_(self, _):
        loc = self.stats.gestureRecognizers()[0].locationInView_(self.stats)
        route = "#today"
        for low, high, r in self.targets:
            if low <= loc.y <= high:
                route = r
                break
        if route == "collapse":
            self.toggle_collapsed()
        elif route == "pick":
            # The line that explains a zero is also the way out of it.
            if self.on_pick:
                self.on_pick()
        else:
            self.open_url(route)

    # --- typing ---

    def controlTextDidChange_(self, note):
        self.tick()

    @objc.python_method
    def tick(self):
        """A soft key sound. Quiet enough to live with, present enough that
        writing here feels like writing somewhere.

        Synthesised rather than borrowed: every system sound macOS offers is
        a high beep with nothing underneath it, which is why the old one
        sounded flimsy at any volume. The fix was spectral, not a level
        change. See keysound.py.
        """
        if not TYPE_SOUND or not self._keys:
            return
        # Round-robin: identical repeats are what make a synthetic key sound
        # like a machine rather than a keyboard.
        self._key_i = (self._key_i + 1) % len(self._keys)
        snd = self._keys[self._key_i]
        snd.setVolume_(KEY_VOLUME)
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
            # PyObjC swallows exceptions raised inside a delegate method, so
            # anything that goes wrong in here looks exactly like Enter not
            # being wired up: no sound, no error, nothing happens. Say what
            # broke and leave the text in the field so it can be retried.
            try:
                return self.submit()
            except Exception as e:
                import traceback
                traceback.print_exc()
                try:
                    with open(ERROR_LOG, "a", encoding="utf-8") as fh:
                        fh.write(traceback.format_exc() + "\n")
                except OSError:
                    pass
                self.flash(t("capture_fail", err=type(e).__name__), False)
                return True

        return False

    @objc.python_method
    def submit(self):
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
            self.feed()
        # The message names the destination rather than wearing a generic
        # prefix: two keys send to two different places, and a confirmation
        # that does not say which leaves you wondering whether the thought
        # reached your notes at all.
        self.flash((info or t("capture_ok")) if ok
                   else t("capture_fail", err=info), ok)
        return True

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
