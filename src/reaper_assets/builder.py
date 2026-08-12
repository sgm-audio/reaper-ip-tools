"""Core RPP builder — emits canonical REAPER 7.x chunks.

Formats are verified against REAPER's own output (the user's installed
Project Templates). Rules enforced here:

- Numeric fields are unquoted and space-separated (``VOLPAN 1 0 -1 -1 1``).
- The master track is a set of ``MASTER_*`` lines, not a ``<TRACK>`` node.
- Every track carries a real UUID in both ``<TRACK {GUID}`` and ``TRACKID {GUID}``.
- Track color is packed as ``ColorToNative(r,g,b) | 0x1000000``.
"""

import time
import uuid

__all__ = [
    "ReaperProjectBuilder",
    "color_to_native",
    "write_envelope",
    "write_master",
    "write_track",
]


def color_to_native(r, g, b):
    """REAPER packed track color: ``r | (g<<8) | (b<<16)``, plus the
    ``0x1000000`` 'custom color' flag REAPER sets on non-default colors."""
    return (r | (g << 8) | (b << 16)) | 0x1000000


class ReaperProjectBuilder:
    """Strict, balanced-node RPP writer. Raises on unbalanced nesting."""

    def __init__(self):
        self.lines = []
        self.indent = 0

    def _emit(self, content):
        self.lines.append("  " * self.indent + content)

    def open(self, tag, *args):
        parts = [tag] + [str(a) for a in args]
        self._emit("<" + " ".join(parts))
        self.indent += 1

    def close(self):
        if self.indent == 0:
            raise ValueError("close() called at root level")
        self.indent -= 1
        self._emit(">")

    def prop(self, key, *values):
        self._emit(" ".join([key] + [str(v) for v in values]))

    def raw(self, line):
        """Emit a pre-formatted line verbatim (e.g. base64 FX state)."""
        self._emit(line)

    def build(self):
        if self.indent != 0:
            raise ValueError(f"{self.indent} unclosed node(s)")
        return "\n".join(self.lines) + "\n"


def write_master(b):
    """Canonical master-track state (``MASTER_*`` lines)."""
    b.prop("MASTERAUTOMODE", 0)
    b.prop("MASTERTRACKHEIGHT", 0, 0)
    b.prop("MASTERPEAKCOL", 16576)
    b.prop("MASTERMUTESOLO", 0)
    b.prop("MASTERHWOUT", 0, 0, 1, 0, 0, 0, 0, -1)
    b.prop("MASTER_NCH", 2, 2)
    b.prop("MASTER_VOLUME", 1, 0, -1, -1, 1)
    b.prop("MASTER_FX", 1)
    b.prop("MASTER_SEL", 0)


def write_envelope(b, tag, active=0, vis=(1, 0, 1), defshape=0):
    """Canonical ``<MASTERPLAYSPEEDENV>`` / ``<TEMPOENVEX>`` envelope node."""
    b.open(tag)
    b.prop("EGUID", f"{{{uuid.uuid4().hex.upper()}}}")
    b.prop("ACT", active, -1)
    b.prop("VIS", *vis)
    b.prop("LANEHEIGHT", 0, 0)
    b.prop("ARM", 0)
    b.prop("DEFSHAPE", defshape, -1, -1)
    b.close()


def _default_peakcol(color):
    return color_to_native(*color) if color else 16576


def write_track(
    b,
    name,
    color=None,
    folder=None,
    receives=None,
    fx=None,
    track_guid=None,
    mainsends=1,
):
    """Emit a canonical ``<TRACK {GUID}>`` node.

    Parameters
    ----------
    name : str
        Track name.
    color : tuple[int, int, int] or None
        RGB track color (None = REAPER default).
    folder : str or None
        One of ``"parent"``, ``"child"``, ``"end"``, or None. See
        ``reaper_assets.routing.isbus_value`` for the ISBUS encoding.
    receives : list or None
        AUXRECV lines, each a string produced by
        ``reaper_assets.routing.auxrecv_line``. Placed after ``PERF 0``.
    fx : list of str or None
        Stock plugin names to attach via ``reaper_assets.fx.write_fx_chain``.
    track_guid : str or None
        Explicit GUID; a fresh UUID is generated when omitted.
    mainsends : int
        ``MAINSEND`` flag — 0 for bus tracks that route via explicit sends
        instead of the hardware master.
    """
    from .routing import isbus_value

    guid = track_guid or str(uuid.uuid4()).upper()

    b.open("TRACK", f"{{{guid}}}")
    b.prop("NAME", f'"{name}"')
    b.prop("PEAKCOL", _default_peakcol(color))
    b.prop("BEAT", -1)
    b.prop("AUTOMODE", 0)
    b.prop("PANLAWFLAGS", 3)
    b.prop("VOLPAN", 1, 0, -1, -1, 1)
    b.prop("MUTESOLO", 0, 0, 0)
    b.prop("IPHASE", 0)
    b.prop("PLAYOFFS", 0, 1)
    b.prop("ISBUS", *isbus_value(folder))
    b.prop("BUSCOMP", 0, 0, 0, 0, 0)
    b.prop("SHOWINMIX", 1, 0.6667, 0.5, 1, 0.5, 0, 0, 0, 0)
    b.prop("FIXEDLANES", 9, 0, 0, 0, 0)
    b.prop("SEL", 0)
    b.prop("REC", 0, 0, 1, 0, 0, 0, 0, 0)
    b.prop("VU", 2)
    b.prop("TRACKHEIGHT", 0, 0, 0, 0, 0, 0, 0)
    b.prop("INQ", 0, 0, 0, 0.5, 100, 0, 0, 100)
    b.prop("NCHAN", 2)
    b.prop("FX", len(fx) if fx else 0)
    b.prop("TRACKID", f"{{{guid}}}")
    b.prop("PERF", 0)

    if receives:
        for line in receives:
            b.raw(line)

    b.prop("MIDIOUT", -1)
    b.prop("MAINSEND", mainsends, 0)

    if fx:
        from .fx import write_fx_chain

        write_fx_chain(b, fx)
    else:
        b.open("FXCHAIN")
        b.prop("SHOW", 0)
        b.prop("LASTSEL", 0)
        b.prop("DOCKED", 0)
        b.close()

    b.close()  # TRACK


def project_header(b, version_string, timestamp=None):
    """Emit the ``<REAPER_PROJECT 0.1 "X.YY/win64" <ts>`` opening line."""
    b.open(
        "REAPER_PROJECT", "0.1", f'"{version_string}"', timestamp or int(time.time())
    )
