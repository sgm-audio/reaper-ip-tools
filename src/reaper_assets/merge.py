"""Idempotent merge: insert missing tracks into an existing .rpp.

Preserves existing tracks, items, automation, and GUIDs — only *adds* tracks
whose names are not already present. Sends are supported among newly added
tracks (existing receives are left untouched to avoid corruption).
"""

import os
import re
import tempfile

from . import builder as B
from . import routing as R

__all__ = ["existing_track_names", "merge_tracks", "merge_tracks_file"]

_NAME_RE = re.compile(r'^\s*NAME\s+(?:"([^"]*)"|\'([^\']*)\'|`([^`]*)`|(\S+))')


def _scan_tracks(text):
    """Return ``(names, total_track_count)`` for depth-1 ``<TRACK`` chunks.

    ``total_track_count`` counts *every* depth-1 ``<TRACK`` chunk (including
    unnamed tracks) so ``AUXRECV`` source indices never drift off-by-one.
    Direct ``NAME`` properties anywhere inside the ``<TRACK`` body (not just
    on the first line) are matched, while ``NAME`` lines inside nested
    ``<ITEM>`` / ``<SOURCE>`` / ``<FXCHAIN>`` chunks are ignored.
    """
    names = []
    track_count = 0
    depth = 0
    in_track = False
    track_name = None

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("|"):
            continue
        if s.startswith("<"):
            if depth == 1 and (s == "<TRACK" or s.startswith("<TRACK ")):
                track_count += 1
                in_track = True
                track_name = None
            depth += 1
            continue
        if s == ">":
            if in_track and depth == 2:
                if track_name is not None:
                    names.append(track_name)
                in_track = False
                track_name = None
            depth = max(0, depth - 1)
            continue
        if in_track and depth == 2 and track_name is None:
            m = _NAME_RE.match(line)
            if m:
                track_name = next(g for g in m.groups() if g is not None)

    return names, track_count


def existing_track_names(text):
    """Return the ordered list of track names already in ``text``.

    Only direct ``NAME`` properties of depth-1 ``<TRACK`` chunks are counted.
    ``NAME`` lines inside nested ``<ITEM>`` / ``<SOURCE>`` / ``<FXCHAIN>``
    nodes are media-item or FX names, not tracks.
    """
    names, _ = _scan_tracks(text)
    return names


def _insertion_index(lines):
    """Index where new track blocks should be inserted (before depth-1 EXTENSIONS / end)."""
    depth = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("|"):
            continue
        if depth == 1 and (s == "<EXTENSIONS" or s.startswith("<EXTENSIONS ")):
            return i
        if s.startswith("<"):
            depth += 1
        elif s == ">":
            depth -= 1
            if depth == 0:
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
        track_guid=spec.get("guid"),
        mainsends=spec.get("mainsends", 1),
        mute=spec.get("mute", False),
        fx_enabled=spec.get("fx_enabled", True),
    )
    return b.build().rstrip("\n")


def _norm(spec):
    return spec if isinstance(spec, dict) else {"name": spec}


def merge_tracks(text, track_specs, routes=None):
    """Insert ``track_specs`` missing from ``text``; return merged text.

    ``track_specs``: list of name-or-dict (same shape as project spec tracks).
    ``routes``: optional list of ``{from, to, mode?, volume?, name?, midi_flags?}``
    restricted to newly added tracks.
    """
    existing_names, base_count = _scan_tracks(text)
    seen = set(existing_names)
    new_specs = []
    for raw_spec in track_specs:
        s = _norm(raw_spec)
        if s["name"] not in seen:
            seen.add(s["name"])
            new_specs.append(s)

    if not new_specs:
        return text

    # Resolve sends among NEW tracks only.
    new_names = [s["name"] for s in new_specs]
    new_name_to_idx = {name: i for i, name in enumerate(new_names)}
    receives = {name: [] for name in new_names}
    for route in routes or []:
        src, dst = route["from"], route["to"]
        if src in new_name_to_idx and dst in new_name_to_idx:
            if src == dst:
                raise ValueError(f"self-send route not allowed: {src!r} -> {dst!r}")
            receives[dst].append(
                R.auxrecv_line(
                    base_count + new_name_to_idx[src],
                    mode=route.get("mode", 0),
                    volume=route.get("volume", 1),
                    name=route.get("name", ""),
                    midi_flags=route.get("midi_flags", 0),
                )
            )

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
    if merged == text:
        return merged
    parent = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(prefix=".merge_", suffix=".rpp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(merged)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return merged
