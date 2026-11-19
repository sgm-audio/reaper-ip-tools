"""Tests for extract_stock_fx.py (stock Cockos FX descriptor extraction)."""

import os

import extract_stock_fx as E

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_extract_stock_fx_from_real_fixtures_strips_indentation():
    entries = E.extract_stock_fx(FIXTURES)
    for name in ("ReaEQ", "ReaComp", "ReaGate", "ReaLimit"):
        assert name in entries, f"missing {name}"
        state = entries[name]["state"]
        assert state, f"{name} has empty state"
        for line in state:
            assert line == line.strip(), f"leading/trailing whitespace in state: {line!r}"


def test_extract_stock_fx_relaxed_grammar_nested_chunks_and_preset_preference(tmp_path):
    # First file has a named preset; second file has a clean default preset ("")
    (tmp_path / "a_named.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.57/win64" 1\n'
        "  <TRACK {G1}\n"
        "    <FXCHAIN\n"
        '      <VST "VST3: ReaEQ (Cockos)" "rea eq.vst3" 2 "Vocal Cut" 1919247729<56535472656571726561657100000000>\n'
        "        AAAA1111\n"
        "        <NESTED\n"
        "          IGNORED_LINE\n"
        "        >\n"
        "        BBBB2222\n"
        "      >\n"
        "    >\n"
        "  >\n"
        ">\n",
        encoding="utf-8",
    )
    entries_one = E.extract_stock_fx(str(tmp_path))
    assert "ReaEQ" in entries_one
    assert entries_one["ReaEQ"]["dll"] == "rea eq.vst3"
    assert entries_one["ReaEQ"]["preset"] == "Vocal Cut"
    assert entries_one["ReaEQ"]["state"] == ["AAAA1111", "BBBB2222"]

    (tmp_path / "b_clean.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.57/win64" 1\n'
        "  <TRACK {G1}\n"
        "    <FXCHAIN\n"
        '      <VST "VST: ReaEQ (Cockos)" reaeq.dll 0 "" 1919247729<56535472656571726561657100000000> ""\n'
        "        CLEANSTATE\n"
        "      >\n"
        "    >\n"
        "  >\n"
        ">\n",
        encoding="utf-8",
    )
    (tmp_path / "c_named_later.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.57/win64" 1\n'
        "  <TRACK {G1}\n"
        "    <FXCHAIN\n"
        '      <VST "VST: ReaEQ (Cockos)" reaeq.dll 0 "Bass Cut" 1919247729<56535472656571726561657100000000> ""\n'
        "        LATERSTATE\n"
        "      >\n"
        "    >\n"
        "  >\n"
        ">\n",
        encoding="utf-8",
    )
    entries = E.extract_stock_fx(str(tmp_path))
    # Clean default preset replaces earlier named preset, and is NOT overwritten by later named preset.
    assert entries["ReaEQ"]["preset"] == ""
    assert entries["ReaEQ"]["state"] == ["CLEANSTATE"]


def test_default_templates_dir_cross_platform(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(E.os, "name", "posix")

    monkeypatch.setattr(E.sys, "platform", "darwin")
    assert E._default_templates_dir().endswith(
        os.path.join("Library", "Application Support", "REAPER", "Project Templates")
    )

    monkeypatch.setattr(E.sys, "platform", "linux")
    assert E._default_templates_dir().endswith(
        os.path.join(".config", "REAPER", "Project Templates")
    )
