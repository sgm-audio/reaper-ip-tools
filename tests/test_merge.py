import pytest

from reaper_assets import merge, validate


def _sample():
    return (
        '<REAPER_PROJECT 0.1 "7.0/win64" 1\n'
        '  <TRACK {GUIDA}\n    NAME "Existing"\n    VOLPAN 1 0 -1 -1 1\n  >\n'
        "  <EXTENSIONS\n  >\n>\n"
    )


def test_merge_inserts_missing_track():
    out = merge.merge_tracks(_sample(), [{"name": "NewTrack"}])
    assert 'NAME "NewTrack"' in out
    assert 'NAME "Existing"' in out  # preserved
    assert validate.validate_rpp(out) == []


def test_merge_is_idempotent():
    once = merge.merge_tracks(_sample(), [{"name": "NewTrack"}])
    twice = merge.merge_tracks(once, [{"name": "NewTrack"}])
    assert twice == once


def test_merge_skips_existing():
    out = merge.merge_tracks(_sample(), [{"name": "Existing"}])
    assert out == _sample()


def test_existing_track_names():
    assert merge.existing_track_names(_sample()) == ["Existing"]


def test_existing_track_names_ignores_item_names():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <TRACK {G1}\n"
        '    NAME "Voice"\n'
        "    <ITEM\n"
        '      NAME "some_media.wav"\n'
        "      SOFFS 0\n"
        "    >\n"
        "  >\n"
        ">\n"
    )
    assert merge.existing_track_names(text) == ["Voice"]


def test_existing_track_names_handles_non_first_line_and_all_quotes():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <TRACK {G1}\n"
        "    PEAKCOL 16576\n"
        "    NAME 'Lead \"Vox\"'\n"
        "  >\n"
        "  <TRACK {G2}\n"
        "    VOLPAN 1 0 -1 -1 1\n"
        "    NAME `Bob's \"Bus\"`\n"
        "  >\n"
        "  <TRACK {G3}\n"
        "    NAME PlainName\n"
        "  >\n"
        ">\n"
    )
    assert merge.existing_track_names(text) == [
        'Lead "Vox"',
        "Bob's \"Bus\"",
        "PlainName",
    ]


def test_merge_track_named_same_as_item_is_not_skipped():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <TRACK {G1}\n"
        '    NAME "Voice"\n'
        "    <ITEM\n"
        '      NAME "Bass"\n'
        "    >\n"
        "  >\n"
        "  <EXTENSIONS\n  >\n>\n"
    )
    out = merge.merge_tracks(text, [{"name": "Bass"}])
    # "Bass" is an item name, so a new "Bass" track must still be added.
    assert out.count('NAME "Bass"') == 2


def test_merge_send_index_counts_unnamed_tracks_and_ignores_items():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <TRACK {G0}\n"
        "    VOLPAN 1 0 -1 -1 1\n"
        "  >\n"
        "  <TRACK {G1}\n"
        '    NAME "OnlyTrack"\n'
        "    <ITEM\n"
        '      NAME "fake1"\n'
        "      <SOURCE WAVE\n"
        '        NAME "fake2"\n'
        "      >\n"
        "    >\n"
        "  >\n"
        "  <EXTENSIONS\n  >\n>\n"
    )
    # base_count must be 2 (unnamed track + "OnlyTrack"), so new A is index 2.
    out = merge.merge_tracks(
        text, [{"name": "A"}, {"name": "B"}], routes=[{"from": "A", "to": "B"}]
    )
    assert "AUXRECV 2 0 1 0 0 0 0 0 0 -1:U 0 -1 ''" in out


def test_merge_adds_sends_and_forwards_route_attributes():
    out = merge.merge_tracks(
        _sample(),
        [{"name": "A"}, {"name": "B"}],
        routes=[{"from": "A", "to": "B", "mode": 3, "volume": 0.5, "name": "Verb"}],
    )
    # A inserted before B; B receives AUXRECV for A (index base_count + 0 = 1)
    assert "AUXRECV 1 3 0.5 0 0 0 0 0 0 -1:U 0 -1 'Verb'" in out


def test_merge_deduplicates_new_track_specs_and_rejects_self_send():
    out = merge.merge_tracks(_sample(), ["Dup", {"name": "Dup"}])
    assert out.count('NAME "Dup"') == 1
    with pytest.raises(ValueError):
        merge.merge_tracks(
            _sample(), ["Loop"], routes=[{"from": "Loop", "to": "Loop"}]
        )


def test_merge_ignores_nested_extensions_chunk():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <TRACK {G1}\n"
        '    NAME "Existing"\n'
        "    <EXTENSIONS\n"
        "      FOO 1\n"
        "    >\n"
        "  >\n"
        "  <EXTENSIONS\n"
        "  >\n"
        ">\n"
    )
    out = merge.merge_tracks(text, ["Added"])
    assert validate.validate_rpp(out) == []
    assert merge.existing_track_names(out) == ["Existing", "Added"]


def test_merge_tracks_file_noop_and_atomic_write(tmp_path):
    rpp = tmp_path / "proj.rpp"
    rpp.write_text(_sample(), encoding="utf-8")
    before = rpp.read_text(encoding="utf-8")

    # No-op returns unchanged text without rewriting
    out = merge.merge_tracks_file(str(rpp), ["Existing"])
    assert out == before

    # Adding a track rewrites atomically and leaves no temp files behind
    out2 = merge.merge_tracks_file(str(rpp), ["Added"])
    assert 'NAME "Added"' in out2
    assert rpp.read_text(encoding="utf-8") == out2
    assert [p.name for p in tmp_path.iterdir()] == ["proj.rpp"]
