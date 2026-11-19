"""Routing chunks: AUXRECV sends and folder (ISBUS) encoding.

Ground truth (REAPER 7.x):

- A send from track A to track B is stored as an ``AUXRECV`` line on the
  *receiver* B, referencing A by 0-based track index, placed between
  ``PERF 0`` and ``MIDIOUT -1``::

      AUXRECV <src_idx> <mode> <vol_linear> <pan> <mute> <mono> <phase> <src_ch> <dst_ch> <panlaw> <midi_flags> <automode> <name>
      AUXRECV 7 0 1 0 0 0 0 0 0 -1:U 0 -1 ''

- Folder hierarchy is encoded on each track via ``ISBUS``::

      parent        ISBUS 1 1
      child         ISBUS 0 0
      last child    ISBUS 2 -1   (marks the end of the folder)

"""

from .builder import rpp_quote

FOLDER_PARENT = "parent"
FOLDER_CHILD = "child"
FOLDER_END = "end"

__all__ = [
    "FOLDER_CHILD",
    "FOLDER_END",
    "FOLDER_PARENT",
    "auxrecv_line",
    "isbus_value",
    "write_auxrecv",
]


def auxrecv_line(src_index, mode=0, volume=1, name="", midi_flags=0):
    """Return a canonical AUXRECV line referencing ``src_index``.

    REAPER column order:
    ``AUXRECV <src_idx> <mode> <vol_linear> <pan> <mute> <mono> <phase>
    <src_ch> <dst_ch> <panlaw> <midi_flags> <automode> <name>``

    ``mode`` follows REAPER send modes (0 = post-fader, 1 = pre-FX,
    3 = pre-fader/post-FX).
    ``volume`` is linear gain (``1`` = 0 dB unity gain, ``0`` = -inf dB).
    ``midi_flags`` controls MIDI send routing (0 = all channels).
    ``name`` is the optional send label.
    """
    name_tok = rpp_quote(name, prefer="'")
    return f"AUXRECV {src_index} {mode} {volume} 0 0 0 0 0 0 -1:U {midi_flags} -1 {name_tok}"


def write_auxrecv(b, src_index, mode=0, volume=1, name="", midi_flags=0):
    """Emit an AUXRECV line onto builder ``b``."""
    b.raw(
        auxrecv_line(
            src_index, mode=mode, volume=volume, name=name, midi_flags=midi_flags
        )
    )


def isbus_value(folder=None):
    """Map a folder role to the ``ISBUS`` argument pair.

    Returns a ``(depth, flag)`` tuple suitable for ``builder.prop("ISBUS", *...)``.
    """
    if folder is None or folder == FOLDER_CHILD:
        return (0, 0)
    if folder == FOLDER_PARENT:
        return (1, 1)
    if folder == FOLDER_END:
        return (2, -1)
    raise ValueError(
        f"Unknown folder role {folder!r}. Expected None, "
        f"{FOLDER_PARENT!r}, {FOLDER_CHILD!r}, or {FOLDER_END!r}"
    )
