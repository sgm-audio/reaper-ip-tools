import json

from reaper_assets import cli


def test_generate_template_respects_name(tmp_path):
    out = tmp_path / "out"
    rc = cli.main(
        ["generate", "--template", "podcast", "--name", "my_show", "-o", str(out)]
    )
    assert rc == 0
    assert (out / "my_show.rpp").exists()
    assert (out / "session_map.md").exists()
    assert (out / "routing_matrix.md").exists()
    assert (out / "track_layout.csv").exists()


def test_generate_requires_template_or_spec(tmp_path):
    rc = cli.main(["generate", "-o", str(tmp_path / "out")])
    assert rc == 2


def test_generate_spec_uses_spec_basename(tmp_path):
    spec = tmp_path / "my_spec.json"
    spec.write_text(json.dumps({"tracks": [{"name": "A"}]}))
    out = tmp_path / "out"
    rc = cli.main(["generate", "--spec", str(spec), "-o", str(out)])
    assert rc == 0
    assert (out / "my_spec.rpp").exists()


def test_generate_missing_spec_file(tmp_path):
    rc = cli.main(
        ["generate", "--spec", str(tmp_path / "nope.json"), "-o", str(tmp_path / "o")]
    )
    assert rc == 1
