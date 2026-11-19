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

_VST_RE = re.compile(
    r'<VST\s+"([^"]+)"\s+(?:"([^"]+)"|(\S+))\s+(\d+)\s+"([^"]*)"\s+(\d+)<([0-9A-Fa-f]+)>(?:\s+"[^"]*")?'
)
# Lines inside a <VST> node that are not part of the plugin state blob.
# REAPER writes FLOAT/FLOATPOS/FXID/WAK/BYPASS around the state; the
# hardcoded descriptors in reaper_assets.fx store only the base64 state
# lines, so the extractor skips these to stay consistent with that shape.
_NON_STATE_PREFIXES = ("FLOAT ", "FLOATPOS ", "FXID ", "WAK ", "BYPASS ")


def _default_templates_dir():
    """Return the platform-appropriate REAPER Project Templates directory."""
    env = os.environ.get("APPDATA")
    if env:
        return os.path.join(env, "REAPER", "Project Templates")
    home = os.path.expanduser("~")
    if os.name == "nt":
        return os.path.join(home, "AppData", "Roaming", "REAPER", "Project Templates")
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/REAPER/Project Templates"
        )
    return os.path.expanduser("~/.config/REAPER/Project Templates")


def extract_stock_fx(templates_dir):
    entries = {}
    if not templates_dir or not os.path.isdir(templates_dir):
        return entries
    files = sorted(f for f in os.listdir(templates_dir) if f.lower().endswith(".rpp"))
    for fn in files:
        path = os.path.join(templates_dir, fn)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        for i, line in enumerate(lines):
            m = _VST_RE.search(line)
            if not m:
                continue
            display, dll_quoted, dll_unquoted, _flags, preset, uid, hexchunk = (
                m.groups()
            )
            dll = dll_quoted or dll_unquoted
            if "(Cockos)" not in display:
                continue
            # Collect the base64 state lines at depth 1 inside the <VST> node.
            state = []
            j = i + 1
            depth = 1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped.startswith("<"):
                    depth += 1
                elif stripped == ">":
                    depth -= 1
                    if depth == 0:
                        break
                elif (
                    depth == 1
                    and stripped
                    and not stripped.startswith(_NON_STATE_PREFIXES)
                ):
                    state.append(stripped)
                j += 1
            short = display
            for prefix in ("VST3: ", "VST: "):
                if short.startswith(prefix):
                    short = short[len(prefix) :]
                    break
            short = short.replace(" (Cockos)", "").strip()
            entry = {
                "display": display,
                "dll": dll,
                "uid": int(uid),
                "hex": hexchunk.upper(),
                "preset": preset,
                "source": fn,
                "state": state,
            }
            if short not in entries or (entries[short]["preset"] != "" and preset == ""):
                entries[short] = entry
    return entries


def main():
    templates_dir = sys.argv[2] if len(sys.argv) > 2 else None
    if not templates_dir:
        templates_dir = _default_templates_dir()
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
