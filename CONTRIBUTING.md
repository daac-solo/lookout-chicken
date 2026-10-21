# Contributing

This is a personal tool, shared as-is because the macOS notes in
[NOTES.md](NOTES.md) were expensive to learn and might save someone else the
same evenings.

That shapes what is useful here:

**Very welcome**
- Corrections to NOTES.md, especially if something behaves differently on
  another macOS version
- New providers — that is the extension point, and yours probably differs
  from mine
- Bug reports with the output of running the bundled binary directly:
  `"dist/Lookout Chicken.app/Contents/MacOS/Lookout Chicken"`

**Probably not**
- Features that make it do more. The restraint is the design: it shows one
  uncomfortable number and otherwise stays quiet. A companion that reports
  everything gets ignored by the second week.
- Anything that makes it initiate rather than react. It does not wander,
  grab the cursor, or interrupt.

**Fork it.** It is small on purpose. If your flow differs, changing the code
is probably faster than persuading me, and the result will fit you better.

No CI, no test suite. Before opening a PR, please confirm the app builds and
the bundled binary launches with no traceback on the demo provider.
