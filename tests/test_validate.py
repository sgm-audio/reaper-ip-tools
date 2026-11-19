import os

from reaper_assets import validate

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_valid_rpp_has_no_errors():
    with open(os.path.join(FIXTURES, "voice_over.rpp"), encoding="utf-8") as f:
        text = f.read()
    assert validate.validate_rpp(text) == []


def test_empty_and_whitespace_return_errors_without_crashing():
    assert validate.validate_rpp("") != []
    assert validate.validate_rpp("   \n\t\n  ") != []


def test_bad_header_detected():
    assert validate.validate_rpp("NOT_A_PROJECT\n>") != []


def test_quoted_numeric_detected_and_notes_or_names_ignored():
    assert (
        validate.validate_rpp('<REAPER_PROJECT 0.1 "7.0" 1\n  VOLPAN "1 0 -1 -1 1"\n>')
        != []
    )
    # Inside <NOTES> or a track NAME, VOLPAN " or angle brackets must not false-positive.
    valid_with_notes = (
        '<REAPER_PROJECT 0.1 "7.0" 1\n'
        "  <NOTES 0 2\n"
        '    |VOLPAN "1 0"\n'
        "    |<not a chunk\n"
        "    |>\n"
        "  >\n"
        "  <TRACK {G1}\n"
        "    NAME 'A -> B> VOLPAN \"1\"'\n"
        "  >\n"
        ">\n"
    )
    assert validate.validate_rpp(valid_with_notes) == []


def test_unbalanced_detected():
    assert validate.validate_rpp('<REAPER_PROJECT 0.1 "7.0" 1\n  <TRACK {G}\n>\n') != []


def test_find_reaper_exe_returns_string_or_none():
    exe = validate.find_reaper_exe()
    assert exe is None or isinstance(exe, str)


def test_find_reaper_exe_linux_uses_which(monkeypatch, tmp_path):
    fake = tmp_path / "reaper"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setattr(validate.os, "name", "posix")
    monkeypatch.setattr(validate.sys, "platform", "linux")
    monkeypatch.setattr(validate.shutil, "which", lambda name: str(fake))
    assert validate.find_reaper_exe() == str(fake)


def test_set_render_file_replaces_existing_or_inserts():
    existing = '<REAPER_PROJECT 0.1 "7.0" 1\n  RENDER_FILE "/user/important.wav"\n>\n'
    replaced = validate._set_render_file(existing, "/tmp/check/out.wav")
    assert "/user/important.wav" not in replaced
    assert '  RENDER_FILE "/tmp/check/out.wav"' in replaced

    missing = '<REAPER_PROJECT 0.1 "7.0" 1\n>\n'
    inserted = validate._set_render_file(missing, "/tmp/check/out.wav")
    assert '  RENDER_FILE "/tmp/check/out.wav"' in inserted
