import os

from reaper_assets import validate

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_valid_rpp_has_no_errors():
    with open(os.path.join(FIXTURES, "voice_over.rpp"), encoding="utf-8") as f:
        text = f.read()
    assert validate.validate_rpp(text) == []


def test_bad_header_detected():
    assert validate.validate_rpp("NOT_A_PROJECT\n>") != []


def test_quoted_numeric_detected():
    assert (
        validate.validate_rpp('<REAPER_PROJECT 0.1 "7.0" 1\n  VOLPAN "1 0 -1 -1 1"\n>')
        != []
    )


def test_unbalanced_detected():
    assert validate.validate_rpp('<REAPER_PROJECT 0.1 "7.0" 1\n  <TRACK {G}\n>\n') != []


def test_find_reaper_exe_returns_string_or_none():
    exe = validate.find_reaper_exe()
    assert exe is None or isinstance(exe, str)
