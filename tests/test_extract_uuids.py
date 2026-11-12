"""Tests for extract_reaper_uuids.py (REAPER ini -> plugin map extraction).

parse_reaper_ini is covered here with a synthetic ini; main() needs a real
REAPER install and is exercised manually.
"""

import builtins
import os

import extract_reaper_uuids as U

_INI = """\
[plugins]
reaeq.dll=1919247729,0,"VST: ReaEQ (Cockos)"
reacomp.dll=1919247213,0,"VST: ReaComp (Cockos)"
some_plugin.vst3=1234567890ABCDEF1234567890ABCDEF,0,"VST3: Some Plugin (Developer)"
# comment lines are ignored
bad line without an equals sign
empty.name=,,
"""


def test_parse_reaper_ini():
    import tempfile

    with tempfile.NamedTemporaryFile(
        "w", suffix=".ini", delete=False, encoding="utf-8"
    ) as f:
        f.write(_INI)
        path = f.name
    try:
        plugins = U.parse_reaper_ini(path)
    finally:
        os.unlink(path)

    assert plugins["VST: ReaEQ (Cockos)"] == {
        "uid": "1919247729",
        "filename": "reaeq.dll",
        "type": "VST",
    }
    assert plugins["VST: ReaComp (Cockos)"]["uid"] == "1919247213"
    assert plugins["VST3: Some Plugin (Developer)"] == {
        "uid": "1234567890ABCDEF1234567890ABCDEF",
        "filename": "some_plugin.vst3",
        "type": "VST3",
    }
    # commas inside the quoted name are kept; surrounding quotes are stripped
    assert plugins[""] == {"uid": "", "filename": "empty.name", "type": "VST"}


def test_get_reaper_resource_path_missing_appdata_does_not_raise(monkeypatch):
    # APPDATA unset must fall through gracefully instead of KeyError.
    monkeypatch.setattr(U.platform, "system", lambda: "Windows")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "/fake/REAPER")
    assert U.get_reaper_resource_path() == "/fake/REAPER"
