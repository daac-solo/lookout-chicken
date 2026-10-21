"""
The cursor-side popup — what the chick shows when you look at it.

Follows tooltip craft rather than notification habit: it waits for the
cursor to actually rest before appearing, fades in gently and out quickly,
flips away from screen edges, and never repositions once visible (jitter
reads worse than a late reposition).
"""

import AppKit
import objc
from Foundation import NSMakeRect, NSObject

PW = 236
PAD = 13
OFF_X = 14      # cursor offset, per tooltip convention
OFF_Y = 10
EDGE_X = 120    # flip horizontally inside this margin
EDGE_Y = 80
FADE_IN = 0.18
FADE_OUT = 0.09


def _screen_at(point):
    """The display the cursor is actually on. Using mainScreen here would
    flip the popup against the wrong edge on a second monitor."""
    for sc in AppKit.NSScreen.screens():
        f = sc.frame()
        if (f.origin.x <= point.x <= f.origin.x + f.size.width
                and f.origin.y <= point.y <= f.origin.y + f.size.height):
            return f
    return AppKit.NSScreen.mainScreen().frame()


class Popup(NSObject):
    def initWithPalette_(self, p):
        self = objc.super(Popup, self).init()
        if self is None:
            return None
        self.p = p
        self.panel = None
        self.body = None
        return self

    @objc.python_method
    def build(self):
        panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PW, 90),
            AppKit.NSWindowStyleMaskBorderless
            | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered, False)
        panel.setLevel_(AppKit.NSStatusWindowLevel + 2)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setIgnoresMouseEvents_(True)   # never steals the pointer
        panel.setAlphaValue_(0.0)
        panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorIgnoresCycle)

        body = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, PW, 90))
        body.setWantsLayer_(True)
        body.layer().setCornerRadius_(13)
        body.layer().setBackgroundColor_(self.p["paper"].CGColor())
        body.layer().setBorderWidth_(1.0)
        body.layer().setBorderColor_(
            self.p["gold"].colorWithAlphaComponent_(0.35).CGColor())
        panel.setContentView_(body)

        self.panel = panel
        self.body = body

    @objc.python_method
    def show(self, lines, at):
        """lines: list of (text, size, color, bold). at: NSPoint cursor."""
        if self.panel is None:
            self.build()
        for v in list(self.body.subviews()):
            v.removeFromSuperview()

        views = []
        for text, size, color, bold in lines:
            f = AppKit.NSTextField.labelWithString_(text)
            f.setFont_(self.p["font"](size, bold))
            f.setTextColor_(color)
            f.setBackgroundColor_(AppKit.NSColor.clearColor())
            f.setFrame_(NSMakeRect(PAD, 0, PW - PAD * 2, size + 6))
            views.append((f, size + 6))

        h = PAD * 2 + sum(x[1] + 4 for x in views) - 4
        y = h - PAD
        for f, fh in views:
            y -= fh
            fr = f.frame()
            f.setFrame_(NSMakeRect(fr.origin.x, y, fr.size.width, fh))
            self.body.addSubview_(f)
            y -= 4

        screen = _screen_at(at)
        x = at.x + OFF_X
        py = at.y - OFF_Y - h
        # Flip rather than run off the edge.
        if x + PW > screen.origin.x + screen.size.width - EDGE_X:
            x = at.x - OFF_X - PW
        if py < screen.origin.y + EDGE_Y:
            py = at.y + OFF_Y

        self.body.setFrame_(NSMakeRect(0, 0, PW, h))
        self.panel.setFrame_display_(NSMakeRect(x, py, PW, h), False)
        self.panel.orderFront_(None)

        AppKit.NSAnimationContext.beginGrouping()
        AppKit.NSAnimationContext.currentContext().setDuration_(FADE_IN)
        self.panel.animator().setAlphaValue_(1.0)
        AppKit.NSAnimationContext.endGrouping()

    @objc.python_method
    def hide(self):
        if self.panel is None:
            return
        AppKit.NSAnimationContext.beginGrouping()
        AppKit.NSAnimationContext.currentContext().setDuration_(FADE_OUT)
        self.panel.animator().setAlphaValue_(0.0)
        AppKit.NSAnimationContext.endGrouping()

    @objc.python_method
    def visible(self):
        return bool(self.panel and self.panel.alphaValue() > 0.1)
