"""Routing chunks: AUXRECV sends and folder (ISBUS) encoding.

Ground truth (REAPER 7.x):

- A send from track A to track B is stored as an ``AUXRECV`` line on the
  *receiver* B, referencing A by 0-based track index, placed between
  ``PERF 0`` and ``MIDIOUT -1``::

      AUXRECV 7 0 0 0 0 0 0 0 0 -1:U 0 -1 ''

- Folder hierarchy is encoded on each track via ``ISBUS``::

      parent        ISBUS 1 1
      child         ISBUS 0 0
      last child    ISBUS 2 -1   (marks the end of the folder)

"""

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


def auxrecv_line(src_index, mode=0, volume=0, name=""):
    """Return a canonical AUXRECV line referencing ``src_index``.

    ``mode`` follows REAPER send modes (0 = post-fader, the default).
    ``volume`` is 0 dB at 0. ``name`` is the optional send label.
    """
    name_tok = f"'{name}'"
    return f"AUXRECV {src_index} 0 {mode} 0 0 0 0 0 0 -1:U {volume} -1 {name_tok}"


def write_auxrecv(b, src_index, mode=0, volume=0, name=""):
    """Emit an AUXRECV line onto builder ``b``."""
    b.raw(auxrecv_line(src_index, mode=mode, volume=volume, name=name))


def isbus_value(folder=None):
    """Map a folder role to the ``ISBUS`` argument pair.

    Returns a ``(depth, flag)`` tuple suitable for ``builder.prop("ISBUS", *...)``.
    """
    if folder == FOLDER_PARENT:
        return (1, 1)
    if folder == FOLDER_END:
        return (2, -1)
    return (0, 0)
