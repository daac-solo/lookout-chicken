"""A keystroke that has a body.

macOS ships no system sound that reads as a key. "Morse" is a thin high
beep with nothing under 1kHz, which is why it sounds flimsy no matter how
the volume is set — the problem is the spectrum, not the level.

A key you believe in is mostly low: a short thump with a fast attack and a
decay under 40ms, with just enough high-frequency noise at the very start to
read as contact. That is synthesised here rather than shipped as an asset,
so there is no binary blob in the repo and the character can be tuned by
reading numbers instead of opening an audio editor.

Several variants are generated and rotated. Identical repeats are what make
a synthetic key sound mechanical; real keys never land twice the same way.
"""

import array
import math
import os
import random
import struct
import wave

RATE = 44100
VARIANTS = 4


def _one(path, seed):
    rnd = random.Random(seed)
    # Low enough to feel like wood or plastic, not a beep. The spread across
    # variants is what stops a fast typist hearing a machine gun.
    body_hz = rnd.uniform(118.0, 152.0)
    dur = rnd.uniform(0.030, 0.038)
    n = int(RATE * dur)
    samples = array.array("h")

    for i in range(n):
        t = i / RATE
        # Exponential decay: a key stops ringing almost at once.
        env = math.exp(-t * 115.0)
        # A slight downward glide reads as something settling into place.
        hz = body_hz * (1.0 - 0.18 * (t / dur))
        body = math.sin(2.0 * math.pi * hz * t)
        # The contact itself: noise, but only in the first few milliseconds.
        click = rnd.uniform(-1.0, 1.0) * math.exp(-t * 900.0) * 0.42
        # A quiet upper partial keeps it from sounding muffled.
        tone = math.sin(2.0 * math.pi * body_hz * 3.1 * t) * 0.10 * math.exp(-t * 300.0)
        v = (body * 0.78 + click + tone) * env
        # Soft clip, so the attack stays punchy without crackling.
        v = math.tanh(v * 1.6) * 0.92
        samples.append(int(max(-1.0, min(1.0, v)) * 32000))

    # A couple of milliseconds of fade at each end: a waveform that starts or
    # stops mid-cycle adds its own click, and it is never the one you wanted.
    fade = int(RATE * 0.0015)
    for i in range(min(fade, len(samples))):
        k = i / fade
        samples[i] = int(samples[i] * k)
        samples[-1 - i] = int(samples[-1 - i] * k)

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


def ensure(dirpath):
    """Write the variants if they are missing; return their paths."""
    os.makedirs(dirpath, exist_ok=True)
    paths = []
    for i in range(VARIANTS):
        p = os.path.join(dirpath, f"key-{i}.wav")
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            try:
                _one(p, seed=1000 + i)
            except Exception:
                continue
        paths.append(p)
    return paths


# --- grain ---------------------------------------------------------------
# A grain landing on paper is not a keystroke: almost no body, a short bright
# tick with a trace of ring. Quieter than the key, because four of them land
# in under a second and the point is texture, not punctuation.

def _grain(path, seed):
    rnd = random.Random(seed)
    hz = rnd.uniform(2100.0, 2900.0)
    dur = rnd.uniform(0.016, 0.024)
    n = int(RATE * dur)
    samples = array.array("h")
    for i in range(n):
        t = i / RATE
        env = math.exp(-t * 320.0)
        tick = rnd.uniform(-1.0, 1.0) * math.exp(-t * 1700.0) * 0.55
        ring = math.sin(2.0 * math.pi * hz * t) * 0.45
        # A little low end so it lands on something rather than in the air.
        body = math.sin(2.0 * math.pi * 260.0 * t) * 0.18 * math.exp(-t * 500.0)
        v = (tick + ring + body) * env
        samples.append(int(max(-1.0, min(1.0, math.tanh(v * 1.3))) * 26000))
    fade = int(RATE * 0.0008)
    for i in range(min(fade, len(samples))):
        k = i / fade
        samples[i] = int(samples[i] * k)
        samples[-1 - i] = int(samples[-1 - i] * k)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


def ensure_grain(dirpath):
    os.makedirs(dirpath, exist_ok=True)
    paths = []
    for i in range(3):
        p = os.path.join(dirpath, f"grain-{i}.wav")
        if not os.path.exists(p) or os.path.getsize(p) < 300:
            try:
                _grain(p, seed=5000 + i)
            except Exception:
                continue
        paths.append(p)
    return paths
