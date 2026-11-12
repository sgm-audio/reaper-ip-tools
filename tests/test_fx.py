import pytest

from reaper_assets import builder as B
from reaper_assets import fx as FX


def test_stock_plugins_have_required_fields():
    for name, desc in FX.STOCK_PLUGINS.items():
        for key in ("display", "dll", "uid", "hex", "state"):
            assert key in desc, f"{name} missing {key}"
        assert desc["state"], f"{name} has empty state"
        assert "Cockos" in desc["display"]


def test_stock_uids_match_reaper_4cc():
    # Stock plugin UIDs are REAPER's registered 4CC codes, verified against
    # tests/fixtures/voice_over.rpp (REAPER 7.57-saved project).
    # Stock plugin UIDs are taken verbatim from REAPER-saved projects
    # (tests/fixtures/voice_over.rpp, REAPER 7.57). Where the uid happens to
    # equal the plugin's 4CC code (big-endian), that is noted.
    # ReaEQ: uid == 0x72656571 (1919247729; 4CC 'reeq')
    assert FX.STOCK_PLUGINS["ReaEQ"]["uid"] == 0x72656571
    # ReaComp: uid == 1919247213 (0x7265636D; fixture-verified)
    assert FX.STOCK_PLUGINS["ReaComp"]["uid"] == 1919247213
    # ReaGate: uid == 0x72656774 (1919248244; 4CC 'regt')
    assert FX.STOCK_PLUGINS["ReaGate"]["uid"] == 0x72656774
    # ReaLimit: uid == 0x726C6D74 (1919708532; 4CC 'rlmt')
    assert FX.STOCK_PLUGINS["ReaLimit"]["uid"] == 0x726C6D74


def test_stock_plugin_lookup():
    assert FX.stock_plugin("ReaEQ") is not None
    assert FX.stock_plugin("Nope") is None


def test_write_fx_chain_emits_vst_nodes():
    b = B.ReaperProjectBuilder()
    FX.write_fx_chain(b, ["ReaEQ", "ReaComp"])
    text = b.build()
    assert text.startswith("<FXCHAIN")
    assert "VST: ReaEQ (Cockos)" in text
    assert "VST: ReaComp (Cockos)" in text
    assert "reaeq.dll" in text
    assert "reacomp.dll" in text
    assert "BYPASS 0 0 0" in text
    assert text.rstrip().endswith(">")


def test_write_fx_chain_rejects_unknown():
    b = B.ReaperProjectBuilder()
    with pytest.raises(KeyError):
        FX.write_fx_chain(b, ["ReaEQ", "NotARealPlugin"])


def test_plugin_resolver(tmp_path):
    import json

    map_path = tmp_path / "map.json"
    map_path.write_text(
        json.dumps(
            {
                "Archetype Gojira (Neural DSP)": {
                    "uid": "ABC123",
                    "filename": "archetype.dll",
                    "type": "VST",
                }
            }
        )
    )
    r = FX.PluginResolver(str(map_path))
    assert r.contains("Archetype Gojira (Neural DSP)")
    assert r.resolve("Archetype Gojira (Neural DSP)")["uid"] == "ABC123"
    assert r.missing(["ReaEQ", "Archetype Gojira (Neural DSP)", "Missing"]) == [
        "Missing"
    ]


def test_plugin_resolver_empty_without_map():
    r = FX.PluginResolver("/nonexistent/map.json")
    assert r.available() == []


def test_vst_node_fxid_wak_placement_matches_reaper():
    # In REAPER-saved projects (e.g. tests/fixtures/voice_over.rpp), each
    # <VST> node is closed with '>', and FXID/WAK follow at FXCHAIN level --
    # they are not nested inside the <VST> node. This emitter must match that.
    b = B.ReaperProjectBuilder()
    FX.write_fx_chain(b, ["ReaEQ", "ReaLimit"])
    lines = b.build().splitlines()

    def vst_indices():
        return [i for i, line in enumerate(lines) if line.strip().startswith("<VST")]

    assert len(vst_indices()) == 2
    for i in vst_indices():
        # line after the state block is the VST closer at FXCHAIN indent
        close = next(j for j in range(i, len(lines)) if lines[j].strip() == ">")
        # FXID then WAK immediately follow the closer, at FXCHAIN level
        assert lines[close + 1].strip().startswith("FXID {"), lines[close:]
        assert lines[close + 2].strip() == "WAK 0 0", lines[close:]
        # the closer must come after at least one state line
        assert close > i + 1


def test_vst_node_line_matches_reaper_grammar():
    b = B.ReaperProjectBuilder()
    FX.write_fx_chain(b, ["ReaEQ"])
    lines = b.build().splitlines()
    vst = next(line for line in lines if line.strip().startswith("<VST"))
    assert "VST: ReaEQ (Cockos)" in vst
    assert "reaeq.dll" in vst
    assert "1919247729<56535472656571726561657100000000>" in vst
