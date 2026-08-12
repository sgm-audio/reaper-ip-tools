"""Named session templates (project specs).

Each entry is a declarative project spec consumed by
``reaper_assets.project.generate_rpp_string``. Folder roles follow the REAPER
ISBUS encoding: a folder is ``"parent"`` + children, with the *last* child
marked ``"end"`` to close the folder.
"""

from . import routing as R

__all__ = ["TEMPLATES", "get_template", "list_templates"]

_RED = (255, 82, 82)
_WHITE = (255, 255, 255)
_GREEN = (122, 219, 98)
_BLUE = (63, 167, 232)
_YELLOW = (244, 211, 94)
_PURPLE = (199, 146, 234)
_RUST = (232, 93, 63)
_ORANGE = (255, 136, 0)
_CYAN = (0, 170, 255)


def _folder(children, parent_extra=None):
    """Build a folder track group. ``children`` is a list of track dicts; the
    last child is automatically marked as the folder end."""
    base = dict(parent_extra or {})
    tracks = [dict(base, folder=R.FOLDER_PARENT)]
    for i, child in enumerate(children):
        c = dict(child)
        if i == len(children) - 1:
            c["folder"] = R.FOLDER_END
        else:
            c.setdefault("folder", R.FOLDER_CHILD)
        tracks.append(c)
    return tracks


TEMPLATES = {
    "podcast": {
        "description": "Per-speaker dialogue tracks into a dialogue bus, plus "
        "music bed and SFX into a show master. Target -16 LUFS.",
        "sample_rate": 48000,
        "bpm": 120,
        "time_sig": (4, 4),
        "notes": [
            "Podcast session template (reaper-assets)",
            "Target: -16 LUFS integrated, 48 kHz / 24-bit WAV",
        ],
        "tracks": [
            {"name": "SHOW_MASTER", "color": _WHITE, "fx": ["ReaComp", "ReaLimit"]},
        ]
        + _folder(
            [
                {"name": "HOST", "color": _RUST},
                {"name": "GUEST 1", "color": _BLUE},
                {"name": "GUEST 2", "color": _GREEN},
            ],
            parent_extra={
                "name": "DIALOGUE_BUS",
                "color": _RED,
                "fx": ["ReaGate", "ReaEQ", "ReaComp"],
                "mainsends": 0,
            },
        )
        + [
            {"name": "MUSIC_BED", "color": _PURPLE, "mainsends": 0},
            {"name": "SFX_LIB", "color": _YELLOW, "mainsends": 0},
        ],
        "routes": [
            {"from": "DIALOGUE_BUS", "to": "SHOW_MASTER"},
            {"from": "MUSIC_BED", "to": "SHOW_MASTER"},
            {"from": "SFX_LIB", "to": "SHOW_MASTER"},
        ],
        "markers": [
            {"pos": 0.0, "name": "Show Start"},
            {"pos": 60.0, "name": "Main Content"},
            {"pos": 300.0, "name": "Outro Start"},
        ],
        "regions": [
            {"start": 0.0, "end": 60.0, "name": "COLD OPEN"},
            {"start": 60.0, "end": 300.0, "name": "MAIN SEGMENT"},
            {"start": 300.0, "end": 330.0, "name": "OUTRO"},
        ],
    },
    "mixing": {
        "description": "Instrument stem folders routed into a mix bus. "
        "Target -14 LUFS (streaming) or per-client spec.",
        "sample_rate": 48000,
        "bpm": 120,
        "time_sig": (4, 4),
        "notes": ["Mixing session template (reaper-assets)"],
        "tracks": [
            {"name": "MIX BUS", "color": _WHITE, "fx": ["ReaComp", "ReaLimit"]},
        ]
        + _folder(
            [
                {"name": "KICK", "color": _RED},
                {"name": "SNARE", "color": _ORANGE},
                {"name": "HATS", "color": _YELLOW},
                {"name": "OVERHEADS", "color": _PURPLE},
            ],
            parent_extra={"name": "DRUM BUS", "color": _RUST, "mainsends": 0},
        )
        + [
            {"name": "BASS", "color": _BLUE, "mainsends": 0},
        ]
        + _folder(
            [
                {"name": "GTR L", "color": _GREEN},
                {"name": "GTR R", "color": _GREEN},
            ],
            parent_extra={"name": "GTR BUS", "color": _CYAN, "mainsends": 0},
        )
        + [
            {"name": "KEYS", "color": _YELLOW, "mainsends": 0},
        ]
        + _folder(
            [
                {"name": "LEAD VOX", "color": _BLUE},
                {"name": "BGV", "color": _PURPLE},
            ],
            parent_extra={"name": "VOX BUS", "color": _RED, "mainsends": 0},
        )
        + _folder(
            [{"name": "REVERB", "color": _CYAN}],
            parent_extra={"name": "FX RETURNS", "color": _WHITE, "mainsends": 0},
        ),
        "routes": [
            {"from": "DRUM BUS", "to": "MIX BUS"},
            {"from": "BASS", "to": "MIX BUS"},
            {"from": "GTR BUS", "to": "MIX BUS"},
            {"from": "KEYS", "to": "MIX BUS"},
            {"from": "VOX BUS", "to": "MIX BUS"},
            {"from": "FX RETURNS", "to": "MIX BUS"},
        ],
        "markers": [
            {"pos": 0.0, "name": "Verse 1"},
            {"pos": 60.0, "name": "Chorus 1"},
            {"pos": 120.0, "name": "Verse 2"},
        ],
    },
    "mastering": {
        "description": "Stereo mix input with a master chain and a muted "
        "reference track. Target -14 LUFS (streaming) / -9 LUFS (club).",
        "sample_rate": 48000,
        "bpm": 120,
        "time_sig": (4, 4),
        "notes": ["Mastering session template (reaper-assets)"],
        "tracks": [
            {
                "name": "MIX INPUT",
                "color": _WHITE,
                "fx": ["ReaEQ", "ReaComp", "ReaLimit"],
            },
            {"name": "REFERENCE", "color": _YELLOW, "mainsends": 0},
        ],
        "routes": [],
        "markers": [{"pos": 0.0, "name": "Track Start"}],
    },
    "live": {
        "description": "Input tracks mirrored to FOH and monitor buses.",
        "sample_rate": 48000,
        "bpm": 120,
        "time_sig": (4, 4),
        "notes": ["Live performance session template (reaper-assets)"],
        "tracks": [
            {"name": "FOH MASTER", "color": _WHITE, "fx": ["ReaLimit"]},
        ]
        + _folder(
            [
                {"name": "VOX 1", "color": _BLUE},
                {"name": "VOX 2", "color": _GREEN},
            ],
            parent_extra={"name": "VOCAL INPUTS", "color": _RED, "mainsends": 0},
        )
        + _folder(
            [
                {"name": "GTR DI", "color": _CYAN},
                {"name": "KEYS", "color": _YELLOW},
                {"name": "DRUMS", "color": _ORANGE},
            ],
            parent_extra={"name": "BAND INPUTS", "color": _PURPLE, "mainsends": 0},
        )
        + [
            # Plain bus (not a folder): a folder track that also carries AUXRECV
            # receives crashes REAPER, so monitor mixing is a flat bus.
            {"name": "MONITOR BUS", "color": _WHITE, "mainsends": 0},
        ],
        "routes": [
            {"from": "VOCAL INPUTS", "to": "FOH MASTER"},
            {"from": "BAND INPUTS", "to": "FOH MASTER"},
            {"from": "VOCAL INPUTS", "to": "MONITOR BUS"},
            {"from": "BAND INPUTS", "to": "MONITOR BUS"},
        ],
        "markers": [{"pos": 0.0, "name": "Set Start"}],
    },
    "scoring": {
        "description": "Stem buses for music, SFX, and dialogue. "
        "Target -23 LUFS (broadcast).",
        "sample_rate": 48000,
        "bpm": 120,
        "time_sig": (4, 4),
        "notes": ["Scoring / post session template (reaper-assets)"],
        "tracks": [
            {"name": "MASTER STEM", "color": _WHITE, "fx": ["ReaComp", "ReaLimit"]},
        ]
        + _folder(
            [
                {"name": "STRINGS", "color": _PURPLE},
                {"name": "BRASS", "color": _YELLOW},
            ],
            parent_extra={"name": "MUSIC STEM", "color": _CYAN, "mainsends": 0},
        )
        + _folder(
            [{"name": "SFX 1", "color": _GREEN}],
            parent_extra={"name": "SFX STEM", "color": _GREEN, "mainsends": 0},
        )
        + _folder(
            [{"name": "DIA 1", "color": _BLUE}],
            parent_extra={"name": "DIALOGUE STEM", "color": _RED, "mainsends": 0},
        ),
        "routes": [
            {"from": "MUSIC STEM", "to": "MASTER STEM"},
            {"from": "SFX STEM", "to": "MASTER STEM"},
            {"from": "DIALOGUE STEM", "to": "MASTER STEM"},
        ],
        "markers": [{"pos": 0.0, "name": "Reel Start"}],
    },
}


def get_template(name):
    if name not in TEMPLATES:
        raise KeyError(f"Unknown template {name!r}. Available: {list_templates()}")
    return TEMPLATES[name]


def list_templates():
    return sorted(TEMPLATES.keys())
