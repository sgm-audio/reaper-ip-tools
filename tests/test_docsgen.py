import os

from reaper_assets import catalog, docsgen


def test_docs_generate_all_files(tmp_path):
    spec = catalog.get_template("podcast")
    outputs = docsgen.generate_docs(spec, str(tmp_path), name="podcast")
    assert set(outputs) == {"session_map.md", "routing_matrix.md", "track_layout.csv"}
    for name in outputs:
        assert os.path.exists(tmp_path / name)


def test_track_layout_csv_schema():
    import csv
    import io

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


def test_color_to_hex():
    assert docsgen.color_to_hex((255, 255, 255)) == "#FFFFFF"
    assert docsgen.color_to_hex((232, 93, 63)) == "#E85D3F"
    assert docsgen.color_to_hex(None) == ""
