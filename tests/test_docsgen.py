import csv
import io
import os

from reaper_assets import catalog, docsgen, routing as R


def test_docs_generate_all_files(tmp_path):
    spec = catalog.get_template("podcast")
    outputs = docsgen.generate_docs(spec, str(tmp_path), name="podcast")
    assert set(outputs) == {"session_map.md", "routing_matrix.md", "track_layout.csv"}
    for name in outputs:
        assert os.path.exists(tmp_path / name)


def test_track_layout_csv_schema_folder_depth_and_types():
    spec = catalog.get_template("podcast")
    out = docsgen.generate_docs(spec, None)
    rows = list(csv.reader(io.StringIO(out["track_layout.csv"])))
    header = rows[0]
    assert header == [
        "track_number",
        "track_name",
        "track_type",
        "folder_level",
        "color_hex",
        "fx_chain_ref",
        "routing_note",
    ]
    assert len(rows) == 1 + len(spec["tracks"])

    by_name = {row[1]: row for row in rows[1:]}
    # SHOW_MASTER receives routes -> bus, level 0
    assert by_name["SHOW_MASTER"][2] == "bus"
    assert by_name["SHOW_MASTER"][3] == "0"
    # DIALOGUE_BUS is folder parent -> bus, level 0
    assert by_name["DIALOGUE_BUS"][2] == "bus"
    assert by_name["DIALOGUE_BUS"][3] == "0"
    # Children and folder end sit at level 1, type audio
    assert by_name["HOST"][2] == "audio"
    assert by_name["HOST"][3] == "1"
    assert by_name["GUEST 2"][2] == "audio"
    assert by_name["GUEST 2"][3] == "1"
    # Tracks after folder end return to level 0, type audio even with mainsends=0
    assert by_name["MUSIC_BED"][2] == "audio"
    assert by_name["MUSIC_BED"][3] == "0"


def test_docs_handles_bare_string_tracks_none_fx_pipes_and_string_time_sig():
    spec = {
        "bpm": 110,
        "time_sig": "6/8",
        "tracks": [
            "Lead | Vox",
            {"name": "Sub | Bus", "fx": None, "folder": R.FOLDER_PARENT},
            {"name": "Child", "folder": R.FOLDER_END},
        ],
        "routes": [{"from": "Lead | Vox", "to": "Child"}],
    }
    outputs = docsgen.generate_docs(spec, None, name="custom")
    assert "110 BPM, 6/8" in outputs["session_map.md"]
    assert r"Lead \| Vox" in outputs["session_map.md"]
    assert r"Lead \| Vox" in outputs["routing_matrix.md"]
    rows = list(csv.reader(io.StringIO(outputs["track_layout.csv"])))
    assert len(rows) == 4
    # Child is a route destination -> bus; Sub | Bus is folder parent -> bus
    assert rows[1][2] == "audio"
    assert rows[2][2] == "bus"
    assert rows[3][2] == "bus"


def test_color_to_hex():
    assert docsgen.color_to_hex((255, 255, 255)) == "#FFFFFF"
    assert docsgen.color_to_hex((232, 93, 63)) == "#E85D3F"
    assert docsgen.color_to_hex(None) == ""
