"""The bird in the menu bar, alive.

A companion that only moves when you open its panel is a picture of a
companion. This one breathes where you can always see it.

But motion in the menu bar is expensive attention, not just expensive
cycles: it sits two inches from whatever you are actually reading, and
anything that moves there had better be telling you something. So the
tempo is not decoration — it is the same four moods the panel uses, in
18 points instead of 72. A quick bob means it has been fed and there is
nothing owing. A slow droop means you have a pile you are not looking at.
You learn to read it out of the corner of your eye, which is the only
reason to animate a menu bar at all.

NSStatusItem takes an image, not a layer, so there is no Core Animation
here. Frames are rendered once per mood and a single timer swaps them.
"""

import math
import os

import AppKit
from Foundation import NSMakeRect, NSMakeSize, NSZeroRect

# The menu bar is 22pt tall on every Mac that runs this; 18 is what every
# other status item uses, and matching them is what makes it look native
# rather than oversized.
SIZE = 18.0

# (period seconds, bob px, tilt degrees, opacity)
# Same table as the panel's chick_idle, scaled: a 5px bob on a 72pt bird is
# a 1.2px bob on an 18pt one, and anything bigger reads as a glitch.
MOODS = {
    "fed":    (0.62, 1.30, 6.0, 1.00),
    "ok":     (2.60, 0.55, 0.0, 1.00),
    "hungry": (3.40, 0.35, -5.0, 0.88),
    # The panel can fade a neglected bird to 0.58 because it sits on paper
    # you chose to open. In the menu bar that reads as a disabled item, not
    # a tired one — so neglect is carried by the lean and the tempo, and the
    # opacity floor stays high enough to look deliberate.
    "droopy": (4.60, 0.22, -11.0, 0.74),
}

# Enough to read as motion, few enough to render instantly at launch.
STEPS = 12

# One tick drives every mood. Tempo comes from how far along the cycle the
# clock has travelled, not from retiming the timer, so a mood change takes
# effect on the next frame instead of restarting the bob mid-air.
TICK = 1.0 / 15.0


def _load(path):
    if not path or not os.path.exists(path):
        return None
    return AppKit.NSImage.alloc().initWithContentsOfFile_(path)


def _frame(base, dy, deg, alpha):
    """One posture of the bird, drawn into a menu-bar-sized image."""
    img = AppKit.NSImage.alloc().initWithSize_(NSMakeSize(SIZE, SIZE))
    img.lockFocus()
    if deg:
        t = AppKit.NSAffineTransform.transform()
        # Pivot at the feet: a bird that rotates about its middle looks like
        # it is being spun, one that rotates about its feet looks like it is
        # leaning.
        t.translateXBy_yBy_(SIZE / 2.0, 1.0)
        t.rotateByDegrees_(deg)
        t.translateXBy_yBy_(-SIZE / 2.0, -1.0)
        t.concat()
    base.drawInRect_fromRect_operation_fraction_(
        NSMakeRect(0, dy, SIZE, SIZE), NSZeroRect,
        AppKit.NSCompositingOperationSourceOver, alpha)
    img.unlockFocus()
    return img


def _cycle(base, mood):
    """A full bob for one mood, as a list of images."""
    _, bob, tilt, alpha = MOODS[mood]
    out = []
    for i in range(STEPS):
        phase = i / float(STEPS)
        # Up fast, down slow: that asymmetry is most of what makes a bob
        # read as a living thing rather than a sine wave.
        lift = math.sin(phase * math.pi) ** 1.6
        sway = math.sin(phase * 2 * math.pi)
        out.append(_frame(base, bob * lift, tilt + sway * 1.4, alpha))
    return out


class MenuBarBird(object):
    """Drives the status item's image.

    Holds no opinion about what the mood means — chicken.py already decides
    that for the panel, and two places deciding it would drift.
    """

    def __init__(self, statusitem, icon_path):
        self.item = statusitem
        self.base = _load(icon_path)
        self.mood = "ok"
        self.frames = {}
        self.timer = None
        self.elapsed = 0.0
        self.shown = -1
        self.flap_until = 0.0
        if self.base is not None:
            # Rendered up front: doing it on the first mood change would
            # stall the main thread at exactly the moment something just
            # arrived and the bird is supposed to react.
            for m in MOODS:
                self.frames[m] = _cycle(self.base, m)

    # --- lifecycle ---

    def start(self):
        if self.base is None or self.timer is not None:
            return
        self.timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            TICK, True, lambda t: self._tick())
        # The menu bar keeps running while you drag a window or scroll, and
        # a bird that freezes during those is worse than one that never
        # moved. Common modes covers both.
        AppKit.NSRunLoop.currentRunLoop().addTimer_forMode_(
            self.timer, AppKit.NSRunLoopCommonModes)

    def stop(self):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None

    # --- state ---

    def set_mood(self, mood):
        if mood in MOODS and mood != self.mood:
            self.mood = mood
            # Force the next tick to redraw even if the frame index happens
            # to match: the image behind that index is a different bird now.
            self.shown = -1

    def flap(self, seconds=1.1):
        """Something just landed. Borrow the fed tempo briefly, whatever the
        mood is — a reaction you can see is the whole point of putting it
        somewhere you are always looking."""
        self.flap_until = self.elapsed + seconds

    # --- the loop ---

    def _tick(self):
        if self.base is None:
            return
        self.elapsed += TICK
        mood = "fed" if self.elapsed < self.flap_until else self.mood
        period = MOODS[mood][0]
        i = int((self.elapsed % period) / period * STEPS) % STEPS
        key = (mood, i)
        if key == self.shown:
            return
        self.shown = key
        try:
            self.item.setImage_(self.frames[mood][i])
        except Exception:
            # A status item can go away during quit; a dead bird should not
            # take the app with it.
            self.stop()
