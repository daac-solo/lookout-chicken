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

No CI, no test suite. Run `./check.sh` before opening a PR: it compiles
every module, checks both string tables are complete and agree on their
placeholders, reads `demo-vault/` through the folder provider, confirms bad
input degrades to zeros rather than raising, and — if you have built one —
launches the bundled binary to see whether it survives eight seconds.

That last one is the check worth keeping. Two builds in this project's short
history crashed on launch while everything else passed, because a menu bar
app's failures are visual and the bundle swallows the traceback.

## Versions

Every change lands in [CHANGELOG.md](CHANGELOG.md) before it is released,
under **Added**, **Changed**, **Fixed** or **Removed**. Write the entry for
somebody deciding whether to upgrade: what is different, and where it is not
obvious, why it was wrong before.

Cutting a release:

```bash
# 1. move the version
echo "0.2.0" > VERSION

# 2. CHANGELOG.md: turn [Unreleased] into the new heading with today's date
# 3. commit, then tag and publish
git commit -am "Release 0.2.0"
git tag -a v0.2.0 -m "0.2.0"
git push && git push --tags
gh release create v0.2.0 --title "0.2.0" --notes-file <(sed -n '/## \[0.2.0\]/,/## \[0.1/p' CHANGELOG.md | sed '$d')
```

`VERSION` is the only place the number lives — `setup.py` reads it into the
bundle, so a build can never claim a version the tag does not match.

The minor number moves when behaviour changes, the patch number when
something is repaired. Before `1.0.0` neither promises compatibility, but
the changelog still has to say what moved.
