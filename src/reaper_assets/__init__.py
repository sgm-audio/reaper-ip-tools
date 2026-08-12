"""reaper-assets: emit canonical, valid REAPER .rpp session templates.

Public API surface:
- builder: ReaperProjectBuilder, color_to_native, write_master, write_envelope, write_track
- project: generate_rpp_project, generate_rpp_string
- fx: stock plugin descriptors + FXCHAIN emission
- routing: AUXRECV send lines + folder (ISBUS) encoding
- markers: MARKER / REGION emission
- catalog: named session templates (podcast, mixing, mastering, live, scoring)
- docsgen: session_map.md / routing_matrix.md / track_layout.csv generation
- merge: idempotent merge of tracks into an existing .rpp
- validate: structural validation + optional REAPER round-trip check
- version: REAPER version detection
- cli: command-line interface (reaper-assets)
"""

from .builder import (
    ReaperProjectBuilder,
    color_to_native,
    write_envelope,
    write_master,
    write_track,
)
from .catalog import TEMPLATES, get_template, list_templates
from .docsgen import generate_docs
from .fx import PluginResolver, stock_plugin, write_fx_chain
from .markers import write_marker, write_region
from .merge import merge_tracks
from .project import generate_rpp_project, generate_rpp_string
from .routing import FOLDER_CHILD, FOLDER_END, FOLDER_PARENT, isbus_value, write_auxrecv
from .validate import validate_rpp, validate_rpp_file
from .version import detect_reaper_version

__version__ = "1.0.0"

__all__ = [
    "FOLDER_CHILD",
    "FOLDER_END",
    "FOLDER_PARENT",
    "TEMPLATES",
    "PluginResolver",
    "ReaperProjectBuilder",
    "__version__",
    "color_to_native",
    "detect_reaper_version",
    "generate_docs",
    "generate_rpp_project",
    "generate_rpp_string",
    "get_template",
    "isbus_value",
    "list_templates",
    "merge_tracks",
    "stock_plugin",
    "validate_rpp",
    "validate_rpp_file",
    "write_auxrecv",
    "write_envelope",
    "write_fx_chain",
    "write_marker",
    "write_master",
    "write_region",
    "write_track",
]
