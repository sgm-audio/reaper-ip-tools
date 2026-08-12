"""Re-extract stock Cockos plugin descriptors from installed REAPER templates.

Scans ``<VST "VST: ... (Cockos)" ...>`` entries in the Project Templates
directory and writes a JSON map of ``name -> {display, dll, uid, hex, preset,
state}``. This is the extensibility companion to ``reaper_assets.fx`` — use it
to refresh the hardcoded state blobs from your own templates.

Usage: python extract_stock_fx.py [output.json] [templates_dir]
"""

import json
import os
import re
import sys

_VST_RE = re.compile(r'<VST "([^"]+)" (\S+) 0 "([^"]*)" (\d+)<([0-9A-Fa-f]+)> ""')
_STATE_START = re.compile(r"^\s*[A-Za-z0-9+/=]{40,}\s*$")


def extract_stock_fx(templates_dir):
    entries = {}
    if not os.path.isdir(templates_dir):
        return entries
    files = sorted(f for f in os.listdir(templates_dir) if f.lower().endswith(".rpp"))
    for fn in files:
        path = os.path.join(templates_dir, fn)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        for i, line in enumerate(lines):
            m = _VST_RE.search(line)
            if not m:
                continue
            display, dll, preset, uid, hexchunk = m.groups()
            if "(Cockos)" not in display:
                continue
            # Collect the base64 state lines inside the <VST> node.
            state = []
            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped == ">":
                    break
                if stripped and not stripped.startswith("<"):
                    state.append(lines[j].rstrip())
                j += 1
            short = display.replace("VST: ", "").replace(" (Cockos)", "")
            entries[short] = {
                "display": display,
                "dll": dll,
                "uid": int(uid),
                "hex": hexchunk.upper(),
                "preset": preset,
                "source": fn,
                "state": state,
            }
    return entries


def main():
    templates_dir = sys.argv[2] if len(sys.argv) > 2 else None
    if not templates_dir:
        templates_dir = os.path.join(
            os.environ.get("APPDATA", ""), "REAPER", "Project Templates"
        )
    out = sys.argv[1] if len(sys.argv) > 1 else "stock_fx_map.json"

    entries = extract_stock_fx(templates_dir)
    if not entries:
        print(f"[WARN] no stock FX found in {templates_dir}")
        return 1
    with open(out, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"[SUCCESS] extracted {len(entries)} stock plugins -> {out}")
    print("  " + ", ".join(sorted(entries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
