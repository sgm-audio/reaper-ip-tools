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
    # ReaEQ 4CC 'reeq' = 1919247729
    assert FX.STOCK_PLUGINS["ReaEQ"]["uid"] == 1919247729
    # ReaComp 4CC 'reacomp' -> 'reac' = 0x72656163 = 1919247213
    assert FX.STOCK_PLUGINS["ReaComp"]["uid"] == 1919247213


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
