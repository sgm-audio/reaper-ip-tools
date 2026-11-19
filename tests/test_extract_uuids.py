"""Tests for extract_reaper_uuids.py (REAPER ini -> plugin map extraction).

parse_reaper_ini and find_vst_ini are covered here with synthetic files;
main() needs a real REAPER install and is exercised manually.
"""

import builtins

import extract_reaper_uuids as U

_INI = """\
[vstcache]
reaeq.dll=001234567890ABCD,1919247729,"VST: ReaEQ (Cockos)"
reacomp.dll=00ABCDEF12345678,1919247213,VST: ReaComp (Cockos)
some_plugin.vst3<12345678>=00AABBCCDD,1234567890ABCDEF1234567890ABCDEF,Some Synth (Developer)!!!VST3i
old_synth.dll=00112233,987654321,Old Synth (Dev)!!!VSTi
comma_plugin.clap=00445566,CLAP_UID_1,"CLAP: My, Plugin (Dev)"
; semicolon comment with = and commas,1,2
# hash comment with = and commas,1,2
bad line without an equals sign
empty_name.dll=00112233,12345,
empty_uid.dll=00112233,,No UID Plugin
"""


def test_parse_reaper_ini(tmp_path):
    ini = tmp_path / "reaper-vstplugins64.ini"
    ini.write_text(_INI, encoding="utf-8")
    plugins = U.parse_reaper_ini(str(ini))

    assert plugins["VST: ReaEQ (Cockos)"] == {
        "uid": "1919247729",
        "filename": "reaeq.dll",
        "type": "VST",
    }
    assert plugins["VST: ReaComp (Cockos)"]["uid"] == "1919247213"
    assert plugins["Some Synth (Developer)"] == {
        "uid": "1234567890ABCDEF1234567890ABCDEF",
        "filename": "some_plugin.vst3<12345678>",
        "type": "VST3",
    }
    assert plugins["Old Synth (Dev)"] == {
        "uid": "987654321",
        "filename": "old_synth.dll",
        "type": "VST",
    }
    assert plugins["CLAP: My, Plugin (Dev)"] == {
        "uid": "CLAP_UID_1",
        "filename": "comma_plugin.clap",
        "type": "CLAP",
    }
    # Comments, empty names, and empty UIDs must be excluded
    assert "" not in plugins
    assert "No UID Plugin" not in plugins
    assert len(plugins) == 5


def test_find_vst_ini_probes_platform_candidates(tmp_path):
    assert U.find_vst_ini(str(tmp_path)) is None
    linux_ini = tmp_path / "reaper-vstplugins_x86_64.ini"
    linux_ini.write_text("[vstcache]\n", encoding="utf-8")
    assert U.find_vst_ini(str(tmp_path)) == str(linux_ini)


def test_get_reaper_resource_path_missing_appdata_and_eof(monkeypatch):
    # APPDATA unset must fall through gracefully instead of KeyError.
    monkeypatch.setattr(U.platform, "system", lambda: "Windows")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "/fake/REAPER")
    assert U.get_reaper_resource_path() == "/fake/REAPER"

    # EOFError on non-interactive stdin returns empty string instead of crashing.
    def _raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", _raise_eof)
    assert U.get_reaper_resource_path() == ""
