import pytest

from reaper_assets import builder as B
from reaper_assets import catalog, project, routing as R, validate


def test_all_templates_generate_valid_rpp():
    for name in catalog.list_templates():
        spec = catalog.get_template(name)
        text = project.generate_rpp_string(spec)
        errors = validate.validate_rpp(text)
        assert errors == [], f"{name}: {errors}"


def test_podcast_routing_and_folders():
    spec = catalog.get_template("podcast")
    text = project.generate_rpp_string(spec)

    # Folder structure: DIALOGUE_BUS parent, GUEST 2 is the folder end.
    assert "ISBUS 1 1" in text
    assert "ISBUS 2 -1" in text
    # Buses route via explicit unity-gain sends.
    assert "AUXRECV 1 0 1 0 0 0 0 0 0 -1:U 0 -1 ''" in text
    # Stock FX present on dialogue + show buses.
    assert "reagate.dll" in text
    assert "realimit.dll" in text
    # Separate 1-based counters for markers and regions; two-line regions.
    assert 'MARKER 1 0 "Show Start" 0 0 1 R {' in text
    assert 'MARKER 1 0 "COLD OPEN" 1 0 1 R {' in text
    assert 'MARKER 1 60 "" 1' in text


def test_routes_resolve_to_auxrecv_on_destination():
    spec = {
        "tracks": [
            {"name": "SRC"},
            {"name": "DST"},
        ],
        "routes": [{"from": "SRC", "to": "DST"}],
    }
    text = project.generate_rpp_string(spec)
    # SRC is index 0; DST receives unity-gain AUXRECV 0.
    assert "AUXRECV 0 0 1 0 0 0 0 0 0 -1:U 0 -1 ''" in text


def test_route_forwards_mode_volume_name_and_midi_flags():
    spec = {
        "tracks": ["SRC", "DST"],
        "routes": [
            {
                "from": "SRC",
                "to": "DST",
                "mode": 3,
                "volume": 0.5,
                "name": "Parallel",
                "midi_flags": 31,
            }
        ],
    }
    text = project.generate_rpp_string(spec)
    assert "AUXRECV 0 3 0.5 0 0 0 0 0 0 -1:U 31 -1 'Parallel'" in text


def test_unknown_route_raises():
    spec = {"tracks": [{"name": "A"}], "routes": [{"from": "A", "to": "ZZZ"}]}
    with pytest.raises(KeyError):
        project.generate_rpp_string(spec)


def test_duplicate_tracks_self_send_folder_target_and_unbalanced_folders_raise():
    with pytest.raises(ValueError):
        project.generate_rpp_string({"tracks": ["A", "A"]})

    with pytest.raises(ValueError):
        project.generate_rpp_string(
            {"tracks": ["A"], "routes": [{"from": "A", "to": "A"}]}
        )

    with pytest.raises(ValueError):
        project.generate_rpp_string(
            {
                "tracks": [
                    {"name": "SRC"},
                    {"name": "FOLDER", "folder": R.FOLDER_PARENT},
                    {"name": "CHILD", "folder": R.FOLDER_END},
                ],
                "routes": [{"from": "SRC", "to": "FOLDER"}],
            }
        )

    with pytest.raises(ValueError):
        project.generate_rpp_string(
            {"tracks": [{"name": "UNCLOSED", "folder": R.FOLDER_PARENT}]}
        )

    with pytest.raises(ValueError):
        project.generate_rpp_string(
            {"tracks": [{"name": "STRAY_END", "folder": R.FOLDER_END}]}
        )


def test_notes_samplerate_timesig_timestamp_and_track_forwarding():
    spec = {
        "sample_rate": 44100,
        "bpm": 95,
        "time_sig": "3/4",
        "timestamp": 0,
        "notes": "Line 1\nLine 2",
        "tracks": [
            {
                "name": "REF",
                "guid": "{AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE}",
                "mute": True,
                "fx_enabled": False,
            }
        ],
        "markers": [{"pos": 0, "name": "Start", "color": (255, 0, 0)}],
        "regions": [{"start": 0, "end": 10, "name": "Intro", "color": (0, 255, 0)}],
    }
    text = project.generate_rpp_string(spec)
    assert validate.validate_rpp(text) == []
    lines = text.splitlines()
    assert lines[0].endswith(" 0")
    assert "    |Line 1" in lines
    assert "    |Line 2" in lines
    assert "  SAMPLERATE 44100 1 0" in lines
    assert "  TEMPO 95 3 4 0" in lines
    assert "  <TRACK {AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE}" in lines
    assert "    MUTESOLO 1 0 0" in lines
    assert "    FX 0" in lines
    assert f'  MARKER 1 0 "Start" 0 {B.color_to_native(255, 0, 0)} 1 R {{' in text
    assert f'  MARKER 1 0 "Intro" 1 {B.color_to_native(0, 255, 0)} 1 R {{' in text
    assert '  MARKER 1 10 "" 1' in lines


def test_catalog_deepcopy_mastering_reference_and_empty_folder():
    t1 = catalog.get_template("podcast")
    t1["tracks"].append({"name": "MUTATED"})
    t2 = catalog.get_template("podcast")
    assert all(tr["name"] != "MUTATED" for tr in t2["tracks"])

    mastering = catalog.get_template("mastering")
    ref = next(tr for tr in mastering["tracks"] if tr["name"] == "REFERENCE")
    assert ref["mute"] is True
    assert ref["mainsends"] == 1
    rpp = project.generate_rpp_string(mastering)
    assert "    MUTESOLO 1 0 0" in rpp

    with pytest.raises(ValueError):
        catalog._folder([])


def test_write_project_to_file(tmp_path):
    out = tmp_path / "test.rpp"
    spec = catalog.get_template("mastering")
    text = project.generate_rpp_project(str(out), spec)
    assert out.exists()
    assert validate.validate_rpp_file(str(out)) == []
    assert text.startswith("<REAPER_PROJECT")


def test_metronome_matches_reaper_ground_truth():
    # REAPER-saved projects write <METRONOME 6 2>; the emitter must match.
    text = project.generate_rpp_string(catalog.get_template("podcast"))
    # REAPER writes the node open line without a trailing '>' on the same
    # line (children follow, then a separate '>').
    assert any(line.strip() == "<METRONOME 6 2" for line in text.splitlines())
