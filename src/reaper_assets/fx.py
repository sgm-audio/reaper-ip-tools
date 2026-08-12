"""FX chunks: verified stock Cockos plugin descriptors and FXCHAIN emission.

Stock plugin state blobs are extracted verbatim from the user's installed
REAPER Project Templates (``voice over.rpp`` and ``NewProject.rpp``) — real,
loadable state, never fabricated.

Third-party plugin identity (VST2/VST3/CLAP) is resolved from
``reaper_plugin_map.json`` (produced by ``extract_reaper_uuids.py``) so that
plugin UIDs are never invented. Full third-party *state* is not reproducible
from the .ini map alone; see ``PluginResolver`` docs.
"""

import json
import os
import uuid

__all__ = [
    "STOCK_PLUGINS",
    "PluginResolver",
    "stock_plugin",
    "write_fx_chain",
    "write_vst_node",
]


STOCK_PLUGINS = {
    "ReaEQ": {
        "display": "VST: ReaEQ (Cockos)",
        "dll": "reaeq.dll",
        "uid": 1919247729,
        "hex": "56535472656571726561657100000000",
        "preset": "",
        "source": "voice over.rpp (vocal low-cut EQ)",
        "state": [
            "cWVlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAAzQAAAAEAAAAAABAA",
            "IQAAAAUAAAAAAAAAAQAAAAAAAAAAAFlAAAAAAAAA8D+amZmZmZnpPwEIAAAAAQAAAAAAAAAAwHJAAAAAAAAA8D8AAAAAAAAAQAEIAAAAAQAAAAAAAAAAQI9AAAAAAAAA",
            "8D8AAAAAAAAAQAEBAAAAAQAAAAAAAAAAiLNAAAAAAAAA8D+amZmZmZnpPwEEAAAAAAAAAAAAAAAAAFlAAAAAAAAA8D8AAAAAAAAAQAEBAAAAAQAAAAAAAAAAAPA/AAAA",
            "AP0BAABcAQAAAgAAAA==",
            "AAAQAAAA",
        ],
    },
    "ReaComp": {
        "display": "VST: ReaComp (Cockos)",
        "dll": "reacomp.dll",
        "uid": 1919247213,
        "hex": "5653547265636D726561636F6D700000",
        "preset": "",
        "source": "voice over.rpp (vocal level control)",
        "state": [
            "bWNlcu9e7f4EAAAAAQAAAAAAAAACAAAAAAAAAAQAAAAAAAAACAAAAAAAAAACAAAAAQAAAAAAAAACAAAAAAAAAFwAAAAAAAAAAAAQAA==",
            "776t3g3wrd4AAJDBAABAQKabxDsK16M8AAAAAAAAAAAAAIA/AAAAAAAAAAAAAAAAnNEHMwAAgD8AAAAAzcxMPQAAAAAAAAAAAAAAAAAAgD4AAAAAAAAAAAAAAAA=",
            "AAAQAAAA",
        ],
    },
    "ReaGate": {
        "display": "VST: ReaGate (Cockos)",
        "dll": "reagate.dll",
        "uid": 1919248244,
        "hex": "56535472656774726561676174650000",
        "preset": "",
        "source": "voice over.rpp (breath/room floor)",
        "state": [
            "dGdlcu9e7f4EAAAAAQAAAAAAAAACAAAAAAAAAAQAAAAAAAAACAAAAAAAAAACAAAAAQAAAAAAAAACAAAAAAAAAFwAAAAAAAAAAAAQAA==",
            "776t3g3wrd6c0QczppvEOwrXozwAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAACc0QczAACAP5zRBzMAAIA/AAAAAAAAAAAAAAAALBYLPwAAAAAAAAAAAAAAAAAAAAA=",
            "AAAQAAAA",
        ],
    },
    "ReaLimit": {
        "display": "VST: ReaLimit (Cockos)",
        "dll": "realimit.dll",
        "uid": 1919708532,
        "hex": "565354726C6D747265616C696D697400",
        "preset": "",
        "source": "NewProject.rpp (true-peak limiter, Program 1)",
        "state": [
            "dG1scu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAAMAAAAAEAAAAAABAA",
            "AwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAD+fduMQw8Y/",
            "AFByb2dyYW0gMQAQAAAA",
        ],
    },
}


def stock_plugin(name):
    """Return the descriptor dict for a stock plugin, or None if unknown."""
    return STOCK_PLUGINS.get(name)


def write_vst_node(b, desc):
    """Emit a single ``<VST ...>`` node from a stock plugin descriptor."""
    b.open(
        "VST",
        f'"{desc["display"]}"',
        desc["dll"],
        0,
        f'"{desc.get("preset", "")}"',
        f"{desc['uid']}<{desc['hex']}>",
        '""',
    )
    for line in desc["state"]:
        b.raw(line)
    b.close()
    b.prop("FXID", f"{{{uuid.uuid4().hex.upper()}}}")
    b.prop("WAK", 0, 0)


def write_fx_chain(b, names):
    """Emit an ``<FXCHAIN>`` wrapping one or more stock plugins by name."""
    unknown = [n for n in names if n not in STOCK_PLUGINS]
    if unknown:
        raise KeyError(
            f"No stock FX descriptor for {unknown}. Available: {sorted(STOCK_PLUGINS)}"
        )

    b.open("FXCHAIN")
    b.prop("SHOW", 0)
    b.prop("LASTSEL", 0)
    b.prop("DOCKED", 0)
    for name in names:
        b.prop("BYPASS", 0, 0, 0)
        write_vst_node(b, STOCK_PLUGINS[name])
    b.close()


class PluginResolver:
    """Resolve plugin names to their real UIDs from ``reaper_plugin_map.json``.

    The map is produced by ``extract_reaper_uuids.py`` from
    ``reaper-vstplugins64.ini`` / ``reaper-clap-win64.ini``. This exists so a
    template can reference a plugin by name without fabricating its UID.

    Note: the .ini map contains *identity only* (uid, filename, type). It does
    not contain plugin *state*, so third-party plugins cannot be emitted with
    their parameter values — only stock Cockos plugins (``STOCK_PLUGINS``) are
    emitted with full, verified state.
    """

    def __init__(self, map_path=None):
        self.map_path = map_path
        self.map = {}
        if map_path and os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    self.map = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.map = {}

    def resolve(self, name):
        """Return ``{"uid", "filename", "type"}`` for ``name``, or None."""
        return self.map.get(name)

    def contains(self, name):
        return name in self.map

    def available(self):
        return sorted(self.map.keys())

    def missing(self, names):
        return [n for n in names if n not in self.map and n not in STOCK_PLUGINS]
