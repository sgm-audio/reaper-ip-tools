from reaper_assets import catalog, project, validate


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
    # Buses route via explicit sends.
    assert "AUXRECV" in text
    # Stock FX present on dialogue + show buses.
    assert "reagate.dll" in text
    assert "realimit.dll" in text
    # Markers and regions.
    assert "MARKER" in text
    assert '"COLD OPEN"' in text


def test_routes_resolve_to_auxrecv_on_destination():
    spec = {
        "tracks": [
            {"name": "SRC"},
            {"name": "DST"},
        ],
        "routes": [{"from": "SRC", "to": "DST"}],
    }
    text = project.generate_rpp_string(spec)
    # SRC is index 0; DST receives AUXRECV 0.
    assert "AUXRECV 0 0 0 0 0 0 0 0 0 -1:U 0 -1 ''" in text


def test_unknown_route_raises():
    spec = {"tracks": [{"name": "A"}], "routes": [{"from": "A", "to": "ZZZ"}]}
    import pytest

    with pytest.raises(KeyError):
        project.generate_rpp_string(spec)


def test_write_project_to_file(tmp_path):
    out = tmp_path / "test.rpp"
    spec = catalog.get_template("mastering")
    text = project.generate_rpp_project(str(out), spec)
    assert out.exists()
    assert validate.validate_rpp_file(str(out)) == []
    assert text.startswith("<REAPER_PROJECT")
