"""MARKER / REGION emission.

Ground truth (REAPER 7.x)::

    # Point marker (flags = 0, single line):
    MARKER 1 0 "Session Start" 0 0 1 R {A30FD8D3-1111-4222-8333-444455556666} 0

    # Region (flags = 1, two lines sharing <idx>):
    MARKER 1 0 "Intro" 1 0 1 R {B40FD8D3-1111-4222-8333-444455556666} 0
    MARKER 1 60 "" 1

Fields: ``MARKER <idx> <pos> <name> <flags> <color> 1 R {<GUID>} 0``.
``flags`` is ``0`` for a point marker and ``1`` for a region (followed by a
closing ``MARKER <idx> <end> "" 1`` line).
"""

import math
import uuid

from .builder import color_to_native, rpp_quote

__all__ = ["marker_line", "region_lines", "write_marker", "write_region"]


def _guid():
    return f"{{{str(uuid.uuid4()).upper()}}}"


def _fmt_time(pos):
    """Format a finite time the way REAPER does: whole numbers as ints
    (``0``, ``30``), fractional values as floats (``30.5``)."""
    f = float(pos)
    if not math.isfinite(f):
        raise ValueError(f"marker/region time must be finite, got {pos!r}")
    if f.is_integer():
        return str(int(f))
    return str(f)


def _normalize_color(color):
    if color is None:
        return 0
    if isinstance(color, (tuple, list)):
        if len(color) != 3:
            raise ValueError(f"RGB color must have 3 channels, got {color!r}")
        return color_to_native(*color)
    return int(color)


def region_lines(idx, start, end, name, color=0):
    """Return REAPER's two-line ``(start_line, end_line)`` pair for a region."""
    start_f = float(start)
    end_f = float(end)
    start_s = _fmt_time(start_f)
    end_s = _fmt_time(end_f)
    if end_f < start_f:
        raise ValueError(f"region end ({end}) must be >= start ({start})")
    col = _normalize_color(color)
    name_tok = rpp_quote(name)
    start_line = f"MARKER {idx} {start_s} {name_tok} 1 {col} 1 R {_guid()} 0"
    end_line = f'MARKER {idx} {end_s} "" 1'
    return (start_line, end_line)


def marker_line(idx, pos, name, color=0, region_end=None):
    """Return a canonical MARKER line, or a two-line REGION block when
    ``region_end`` is provided."""
    if region_end is not None:
        start_line, end_line = region_lines(idx, pos, region_end, name, color=color)
        return f"{start_line}\n{end_line}"
    pos_s = _fmt_time(pos)
    col = _normalize_color(color)
    name_tok = rpp_quote(name)
    return f"MARKER {idx} {pos_s} {name_tok} 0 {col} 1 R {_guid()} 0"


def write_marker(b, idx, pos, name, color=0):
    b.raw(marker_line(idx, pos, name, color=color))


def write_region(b, idx, start, end, name, color=0):
    start_line, end_line = region_lines(idx, start, end, name, color=color)
    b.raw(start_line)
    b.raw(end_line)
