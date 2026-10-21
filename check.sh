#!/bin/bash
# What CONTRIBUTING asks for before a PR, as one command.
#
# There is no test suite, because the thing being tested is a menu bar app
# whose failures are visual. What can be checked mechanically is checked
# here: that it compiles, that the provider reads a known folder correctly,
# that both string tables are complete, and — the one that matters — that
# the bundled binary actually launches without a traceback. Two releases in
# this project's short history crashed on launch while every other check
# passed.
set -e
cd "$(dirname "$0")"
PY=./.venv/bin/python
[ -x "$PY" ] || { echo "run: python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt"; exit 1; }

echo "→ compile"
$PY -m py_compile chicken.py widget.py popup.py hotkeys.py config.py strings.py \
    providers/__init__.py providers/demo.py providers/folder.py providers/http.py

echo "→ strings complete in both languages"
$PY - <<'EOF'
import re, io, sys, strings
zh, en = set(strings.ZH), set(strings.EN)
assert not zh ^ en, f"only in one table: {sorted(zh ^ en)}"
used = set()
for f in ("chicken.py", "widget.py", "popup.py", "config.py", "providers/http.py"):
    try: used |= set(re.findall(r"""\bt\(\s*["']([a-z0-9_]+)["']""", io.open(f, encoding="utf-8").read()))
    except OSError: pass
assert not used - zh, f"used but undefined: {sorted(used - zh)}"
for k in zh & en:
    a = set(re.findall(r"\{(\w+)", str(strings.ZH[k])))
    b = set(re.findall(r"\{(\w+)", str(strings.EN[k])))
    assert a == b, f"{k}: placeholders differ {sorted(a)} vs {sorted(b)}"
print(f"   {len(zh)} keys, both languages")
EOF

echo "→ folder provider reads demo-vault"
$PY - <<'EOF'
import providers.folder as f
f._cache.update({"key": None, "at": 0, "value": None})
d = f.fetch({"folder": {"path": "demo-vault"}})
r = d["ready"]
assert r["count"] == 4, r
assert d["library"] == 14, d["library"]
assert r["oldestDays"] > 100, r
print(f"   ready={r['count']} oldest={r['oldestDays']}d library={d['library']}")
EOF

echo "→ bad input degrades instead of raising"
$PY - <<'EOF'
import providers.folder as f
for cfg in (None, {}, {"folder": {"path": "/nope"}}, {"folder": {"path": ""}}):
    f._cache.update({"key": None, "at": 0, "value": None})
    assert f.fetch(cfg)["ready"]["count"] == 0
print("   zeros, no exception")
EOF

echo "→ README links point at files that exist"
$PY - <<'EOF'
import re, io, os, sys
bad = [m for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", io.open("README.md", encoding="utf-8").read())
       if not m.startswith("http") and not os.path.exists(m)]
assert not bad, f"broken image links: {bad}"
print("   ok")
EOF

if [ -d dist ]; then
  APP=$(ls -d dist/*.app 2>/dev/null | head -1)
  if [ -n "$APP" ]; then
    echo "→ bundled binary launches"
    BIN="$APP/Contents/MacOS/$(basename "${APP%.app}")"
    LOG=$(mktemp)
    "$BIN" > "$LOG" 2>&1 &
    P=$!
    sleep 8
    if kill -0 $P 2>/dev/null; then kill $P; echo "   no traceback in 8s";
    else echo "   FAILED — it exited:"; cat "$LOG"; exit 1; fi
    rm -f "$LOG"
  fi
else
  echo "→ no dist/ yet; run ./.venv/bin/python setup.py py2app to check the bundle too"
fi

echo "all checks passed"
