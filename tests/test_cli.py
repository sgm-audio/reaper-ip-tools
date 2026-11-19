import json

import pytest

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


def test_generate_rejects_both_template_and_spec(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({"tracks": ["A"]}))
    with pytest.raises(SystemExit) as exc:
        cli.main(["generate", "--template", "podcast", "--spec", str(spec)])
    assert exc.value.code == 2


def test_generate_spec_uses_spec_basename(tmp_path):
    spec = tmp_path / "my_spec.json"
    spec.write_text(json.dumps({"tracks": [{"name": "A"}]}))
    out = tmp_path / "out"
    rc = cli.main(["generate", "--spec", str(spec), "-o", str(out)])
    assert rc == 0
    assert (out / "my_spec.rpp").exists()


def test_generate_missing_or_invalid_spec_and_unknown_template(tmp_path):
    assert (
        cli.main(
            [
                "generate",
                "--spec",
                str(tmp_path / "nope.json"),
                "-o",
                str(tmp_path / "o"),
            ]
        )
        == 1
    )

    non_dict = tmp_path / "list.json"
    non_dict.write_text("[1, 2, 3]")
    assert (
        cli.main(["generate", "--spec", str(non_dict), "-o", str(tmp_path / "o2")]) == 1
    )

    # Invalid spec must fail BEFORE creating output directory/files
    bad_spec = tmp_path / "bad_route.json"
    bad_spec.write_text(
        json.dumps({"tracks": ["A"], "routes": [{"from": "A", "to": "A"}]})
    )
    out_dir = tmp_path / "should_not_exist"
    assert cli.main(["generate", "--spec", str(bad_spec), "-o", str(out_dir)]) == 1
    assert not out_dir.exists()

    assert (
        cli.main(
            ["generate", "--template", "nonexistent", "-o", str(tmp_path / "o3")]
        )
        == 1
    )


def test_merge_reports_actual_added_count(tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["generate", "--template", "mastering", "-o", str(out)]) == 0
    rpp = out / "mastering.rpp"
    capsys.readouterr()

    assert cli.main(["merge", str(rpp), "--track", "EXTRA"]) == 0
    assert "merged 1 track(s)" in capsys.readouterr().out

    # Second run is idempotent -> reports 0 added
    assert cli.main(["merge", str(rpp), "--track", "EXTRA"]) == 0
    assert "merged 0 track(s)" in capsys.readouterr().out


def test_validate_and_check_plugins_error_paths(tmp_path):
    assert cli.main(["validate", str(tmp_path / "missing.rpp")]) == 1
    assert (
        cli.main(
            [
                "check-plugins",
                "--template",
                "podcast",
                "--map",
                str(tmp_path / "missing.json"),
            ]
        )
        == 1
    )

    bad_map = tmp_path / "bad.json"
    bad_map.write_text("{invalid")
    assert (
        cli.main(
            ["check-plugins", "--template", "podcast", "--map", str(bad_map)]
        )
        == 1
    )

    assert cli.main(["check-plugins", "--template", "podcast"]) == 0
