import math
import re

import pytest

from reaper_assets import builder as B
from reaper_assets import markers as M

_MARKER_RE = re.compile(
    r'^MARKER 1 0 "Session Start" 0 0 1 R '
    r"\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\} 0$"
)
_REGION_START_RE = re.compile(
    r'^MARKER 1 0 "Intro" 1 0 1 R '
    r"\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\} 0$"
)


def test_marker_line_format():
    line = M.marker_line(1, 0.0, "Session Start")
    assert _MARKER_RE.match(line), line


def test_region_emits_two_reaper_lines():
    block = M.marker_line(1, 0.0, "Intro", region_end=60.0)
    lines = block.splitlines()
    assert len(lines) == 2
    assert _REGION_START_RE.match(lines[0]), lines[0]
    assert lines[1] == 'MARKER 1 60 "" 1'


def test_region_fractional_end():
    start_line, end_line = M.region_lines(1, 0.5, 30.5, "Intro")
    assert start_line.startswith('MARKER 1 0.5 "Intro" 1 0 1 R {')
    assert end_line == 'MARKER 1 30.5 "" 1'


def test_region_rejects_end_before_start():
    with pytest.raises(ValueError):
        M.region_lines(1, 60.0, 30.0, "Backwards")


def test_marker_rejects_non_finite_times():
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            M.marker_line(1, bad, "Bad")
        with pytest.raises(ValueError):
            M.region_lines(1, 0.0, bad, "Bad")


def test_marker_color_rgb_and_quoting():
    line = M.marker_line(2, 10.0, 'Cue "A"', color=(255, 0, 0))
    expected_col = B.color_to_native(255, 0, 0)
    assert f"MARKER 2 10 'Cue \"A\"' 0 {expected_col} 1 R {{" in line


def test_write_marker_and_region_into_builder():
    b = B.ReaperProjectBuilder()
    b.open("REAPER_PROJECT", "0.1", '"7.0"', 0)
    M.write_marker(b, 1, 0.0, "Start")
    M.write_region(b, 1, 0.0, 30.0, "Verse")
    b.close()
    lines = b.build().splitlines()
    assert any(line.startswith('  MARKER 1 0 "Start" 0 0 1 R {') for line in lines)
    assert any(line.startswith('  MARKER 1 0 "Verse" 1 0 1 R {') for line in lines)
    assert '  MARKER 1 30 "" 1' in lines
