# macOS / PyObjC notes

Things that cost real debugging time here. Most produce no error message, or
one that points nowhere near the actual cause.

---

## Accessibility is granted per binary, and ad-hoc rebuilds invalidate it

**Symptom:** hotkeys worked, you rebuilt, now they do not. The app still
appears in the Accessibility list, still switched on.

TCC keys the grant on the code signature, not the path or the bundle ID
alone. An unsigned or freshly ad-hoc-signed rebuild has a different hash, so
the system sees a different program wearing the same name.

**Fix:** sign every build with the same identifier.

```bash
codesign --force --deep --sign - \
  --identifier com.lookoutchicken.app \
  "/Applications/Lookout Chicken.app"
```

If it still fails, remove the stale entry from the Accessibility list with
`−` before re-adding. Toggling it off and on is not enough.

Granting to a bare script means granting to `Python` itself — shared with
every other Python tool on the machine. That is the real reason this ships
as a bundle.

---

## Methods taking arguments need `@objc.python_method`

**Symptom:** `BadPrototypeError` at class-definition time.

PyObjC treats every method on an `NSObject` subclass as a potential
Objective-C selector, and selector arity is encoded in the name. A plain
`def render(self, data)` claims to be the zero-argument selector `render`
while having one parameter.

```python
@objc.python_method
def render(self, data):   # pure Python, invisible to the ObjC runtime
    ...

def clicked_(self, sender):   # a real selector: clicked:
    ...
```

Rule of thumb: if the Objective-C runtime does not need to call it, mark it.

---

## `addAnimation:forKey:` — animation first

**Symptom:** `-[__NSCFString length]: unrecognized selector` from somewhere
inside AppKit, nowhere near your code.

```python
layer.addAnimation_forKey_(animation, "breathe")   # correct
layer.addAnimation_forKey_("breathe", animation)   # crashes later, elsewhere
```

Reversed, CoreAnimation stores a string where it expects an animation and
only discovers this when it next walks its animation list.

---

## Never truth-test an Objective-C object

**Symptom:** the same `unrecognized selector ... length` on a type that has
no business being asked for a length.

```python
if layer.animationForKey_("breathe"):            # probes -length / -count
if layer.animationForKey_("breathe") is not None:  # correct
```

Python's truthiness protocol tries `__len__`, which PyObjC bridges to
`-length`. Classes like `CABasicAnimation` do not implement it. Compare to
`None` explicitly.

---

## Carbon hotkeys register fine and never fire

`RegisterEventHotKey` is the documented way to get global hotkeys without
Accessibility permission. Inside a rumps/PyObjC runloop it returns success
and the handler is never called — there is no error to catch.

This project uses `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_`
instead, which works but requires the permission. Both a global **and** a
local monitor are installed: the global one does not see your own windows,
so without the local one the hotkeys die the moment your panel has focus.

---

## Borderless panels refuse key status

A text field inside `NSWindowStyleMaskBorderless` cannot be typed into,
with no indication why. Subclass and say otherwise:

```python
class KeyPanel(AppKit.NSPanel):
    def canBecomeKeyWindow(self):
        return True
```

---

## Text editing shortcuts need a main menu

`⌘A`, `⌘C`, `⌘V`, `⌘Z` route through the application menu bar. A rumps app
has no main menu, so inside its text fields they silently do nothing. Build
a minimal Edit menu at startup — see `install_edit_menu()`.

---

## `rumps` swallows exceptions in menu callbacks

A failing menu item looks exactly like a menu item that does nothing. Wrap
callback bodies in try/except and log, or spend an evening wondering why a
click has no effect.

The same applies to anything reached from a callback: a crash in `rebuild()`
during `__init__` shows up as a bare "Launch error" dialog from py2app, with
the real traceback only visible by running the bundled binary directly:

```bash
"dist/Lookout Chicken.app/Contents/MacOS/Lookout Chicken"
```

---

## Initialisation order

`rumps.App.__init__` can trigger menu construction before your own
attributes exist. Set everything `rebuild()` reads *before* calling it. Two
separate launch crashes here came from exactly this.

---

## The notch has no pixels

You cannot draw inside the camera cutout — there is no display there. The
"island" effect works by matching the notch's pure black and sitting flush
against its bottom edge with the top corners squared, so the eye reads one
continuous shape.

```python
layer.setMaskedCorners_(kCALayerMinXMinYCorner | kCALayerMaxXMinYCorner)
```

Those constants live in `Quartz`, not `AppKit`.

Also: `NSScreen.mainScreen()` follows the focused window, so on a
multi-display setup it wanders onto the monitor that has no notch. Find the
right screen by checking `safeAreaInsets().top > 0`.

---

## Window level decides whether it is ever seen

A panel at desktop level is hidden by the first window that covers it, which
defeats an ambient reminder entirely. `NSFloatingWindowLevel` sits above
ordinary windows without stealing focus. The island needs
`NSStatusWindowLevel + 1` to clear the menu bar.
