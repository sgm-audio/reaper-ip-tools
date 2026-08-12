from reaper_assets import merge


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


def test_merge_send_index_ignores_items():
    text = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
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
    # base_count must be 1 (only "OnlyTrack"), so the new source index is 1.
    out = merge.merge_tracks(
        text, [{"name": "A"}, {"name": "B"}], routes=[{"from": "A", "to": "B"}]
    )
    assert "AUXRECV 1 0 0 0 0 0 0 0 0 -1:U 0 -1 ''" in out


def test_merge_adds_sends_among_new_tracks():
    out = merge.merge_tracks(
        _sample(),
        [{"name": "A"}, {"name": "B"}],
        routes=[{"from": "A", "to": "B"}],
    )
    # A inserted before B; B receives AUXRECV for A (index base_count + 0)
    assert "AUXRECV 1 0 0 0 0 0 0 0 0 -1:U 0 -1 ''" in out
