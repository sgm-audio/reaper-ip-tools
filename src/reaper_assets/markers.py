"""MARKER / REGION emission.

Ground truth (REAPER 7.x)::

    MARKER 1 0 "Session Start" 0 255 1 R {A30FD8D3-...} 0 2

Fields: ``MARKER <idx> <pos> "<name>" <idnum> <color> <flags> R {GUID}
<mute> <lock>``. A *region* appends its end time as the final field.
"""

import uuid

__all__ = ["marker_line", "write_marker", "write_region"]


def _guid():
    return f"{{{uuid.uuid4().hex.upper()}}}"


def _fmt_time(pos):
    """Format a time the way REAPER does: whole numbers as ints (``0``, ``30``),
    fractional values as floats (``30.5``)."""
    f = float(pos)
    if f.is_integer():
        return str(int(f))
    return str(f)


def marker_line(idx, pos, name, color=255, idnum=0, region_end=None):
    """Return a canonical MARKER (or REGION) line.

    If ``region_end`` is not None the line is a region spanning ``pos`` to
    ``region_end``.
    """
    pos = _fmt_time(pos)
    end = f" {_fmt_time(region_end)}" if region_end is not None else ""
    return f'MARKER {idx} {pos} "{name}" {idnum} {color} 1 R {_guid()} 0 2{end}'


def write_marker(b, idx, pos, name, color=255, idnum=0):
    b.raw(marker_line(idx, pos, name, color=color, idnum=idnum))


def write_region(b, idx, start, end, name, color=255, idnum=0):
    b.raw(marker_line(idx, start, name, color=color, idnum=idnum, region_end=end))
