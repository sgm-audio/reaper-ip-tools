"""Idempotent merge: insert missing tracks into an existing .rpp.

Preserves existing tracks, items, automation, and GUIDs — only *adds* tracks
whose names are not already present. Sends are supported among newly added
tracks (existing receives are left untouched to avoid corruption).
"""

import re

from . import builder as B
from . import routing as R

__all__ = ["existing_track_names", "merge_tracks", "merge_tracks_file"]

_NAME_RE = re.compile(r'^\s*NAME\s+(?:"([^"]*)"|(\S+))')


def existing_track_names(text):
    """Return the ordered list of track names already in ``text``.

    Only ``NAME`` lines that directly follow a ``<TRACK`` opener are counted.
    ``NAME`` lines inside nested ``<ITEM>`` / ``<SOURCE>`` / ``<FXCHAIN>``
    nodes are media-item or FX names, not tracks.
    """
    names = []
    expect_name = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("<TRACK"):
            expect_name = True
            continue
        if not expect_name:
            continue
        if s.startswith("<"):
            expect_name = False
            continue
        m = _NAME_RE.match(line)
        if m:
            names.append(m.group(1) if m.group(1) is not None else m.group(2))
        expect_name = False
    return names


def _insertion_index(lines):
    """Index where new track blocks should be inserted (before EXTENSIONS / end)."""
    for i, line in enumerate(lines):
        if line.lstrip().startswith("<EXTENSIONS"):
            return i
    # fall back: before the final closing '>'
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].rstrip() == ">":
            return i
    return len(lines)


def _indent_block(block, pad="  "):
    return "\n".join(pad + line if line else line for line in block.splitlines())


def _track_block(spec, receives):
    b = B.ReaperProjectBuilder()
    B.write_track(
        b,
        spec["name"],
        color=spec.get("color"),
        folder=spec.get("folder"),
        receives=receives,
        fx=spec.get("fx") or [],
        mainsends=spec.get("mainsends", 1),
    )
    return b.build().rstrip("\n")


def _norm(spec):
    return spec if isinstance(spec, dict) else {"name": spec}


def merge_tracks(text, track_specs, routes=None):
    """Insert ``track_specs`` missing from ``text``; return merged text.

    ``track_specs``: list of name-or-dict (same shape as project spec tracks).
    ``routes``: optional list of ``{from, to}`` restricted to newly added tracks.
    """
    existing = set(existing_track_names(text))
    specs = [_norm(t) for t in track_specs]
    new_specs = [s for s in specs if s["name"] not in existing]

    if not new_specs:
        return text

    base_count = len(existing_track_names(text))

    # Resolve sends among NEW tracks only.
    receives = {name: [] for name in (s["name"] for s in new_specs)}
    for route in routes or []:
        src, dst = route["from"], route["to"]
        new_names = [s["name"] for s in new_specs]
        if src in new_names and dst in new_names:
            receives[dst].append(R.auxrecv_line(base_count + new_names.index(src)))

    blocks = [
        _indent_block(_track_block(s, receives.get(s["name"], [])), "  ")
        for s in new_specs
    ]

    lines = text.splitlines()
    idx = _insertion_index(lines)
    lines[idx:idx] = blocks
    return "\n".join(lines) + "\n"


def merge_tracks_file(path, track_specs, routes=None):
    """Merge tracks into the .rpp at ``path`` in place; returns merged text."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    merged = merge_tracks(text, track_specs, routes=routes)
    with open(path, "w", encoding="utf-8") as f:
        f.write(merged)
    return merged
