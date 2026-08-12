"""Auto-generate session documentation from a project spec.

Produces ``session_map.md``, ``routing_matrix.md``, and ``track_layout.csv``
in the style required by the reaper-session-architect workflow.
"""

import csv
import io
import os

from . import routing as R

__all__ = ["color_to_hex", "generate_docs"]


def color_to_hex(color):
    if not color:
        return ""
    r, g, b = color
    return f"#{r:02X}{g:02X}{b:02X}"


def _title(name):
    return name.replace("_", " ").title()


def _session_map(spec, name):
    lines = []
    lines.append(f"# {_title(name)} Session Map")
    lines.append("")
    lines.append(f"> {spec.get('description', '')}")
    lines.append("")
    lines.append(f"- Sample rate: {spec.get('sample_rate', 48000)} Hz")
    lines.append(
        f"- Tempo: {spec.get('bpm', 120)} BPM, "
        f"{spec.get('time_sig', (4, 4))[0]}/{spec.get('time_sig', (4, 4))[1]}"
    )
    lines.append("")
    lines.append("## Track layout")
    lines.append("")
    lines.append("| # | Track | Color | Folder | FX |")
    lines.append("|---|-------|-------|--------|----|")
    for i, t in enumerate(spec.get("tracks", []), start=1):
        fx = ", ".join(t.get("fx", [])) or "—"
        folder = {"parent": "folder", "end": "folder (end)", "child": "child"}.get(
            t.get("folder"), ""
        )
        lines.append(
            f"| {i} | {t['name']} | {color_to_hex(t.get('color')) or 'default'} "
            f"| {folder or '—'} | {fx} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _routing_matrix(spec):
    lines = []
    lines.append("# Routing Matrix")
    lines.append("")
    routes = spec.get("routes", [])
    if not routes:
        lines.append("No explicit sends (folder or master routing only).")
        lines.append("")
        return "\n".join(lines) + "\n"
    lines.append("| Source | Destination | Mode |")
    lines.append("|--------|-------------|------|")
    for r in routes:
        lines.append(f"| {r['from']} | {r['to']} | {r.get('mode', 0)} |")
    lines.append("")
    lines.append(
        "> Folder children route to their parent implicitly; only "
        "explicit AUXRECV sends are listed above."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def _track_layout_csv(spec):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "track_number",
            "track_name",
            "track_type",
            "folder_level",
            "color_hex",
            "fx_chain_ref",
            "routing_note",
        ]
    )
    for i, t in enumerate(spec.get("tracks", []), start=1):
        folder = t.get("folder")
        folder_level = 0
        if folder == R.FOLDER_PARENT:
            folder_level = 1
        elif folder == R.FOLDER_END:
            folder_level = 0
        fx = ",".join(t.get("fx", []))
        note = _route_note(t["name"], spec.get("routes", []), folder)
        w.writerow(
            [
                i,
                t["name"],
                "bus" if t.get("mainsends") == 0 else "audio",
                folder_level,
                color_to_hex(t.get("color")),
                fx,
                note,
            ]
        )
    return buf.getvalue()


def _route_note(name, routes, folder):
    notes = []
    for r in routes:
        if r["to"] == name:
            notes.append(f"receives {r['from']}")
        elif r["from"] == name:
            notes.append(f"sends to {r['to']}")
    if folder == R.FOLDER_PARENT:
        notes.append("folder parent")
    return "; ".join(notes)


def generate_docs(spec, out_dir, name="session"):
    """Write ``session_map.md``, ``routing_matrix.md``, ``track_layout.csv``.

    Returns a dict of ``{relative_path: content}`` and also writes the files
    to ``out_dir`` when it is not None.
    """
    os.makedirs(out_dir, exist_ok=True) if out_dir else None
    outputs = {
        "session_map.md": _session_map(spec, name),
        "routing_matrix.md": _routing_matrix(spec),
        "track_layout.csv": _track_layout_csv(spec),
    }
    if out_dir:
        for rel, content in outputs.items():
            with open(
                os.path.join(out_dir, rel), "w", encoding="utf-8", newline=""
            ) as f:
                f.write(content)
    return outputs
