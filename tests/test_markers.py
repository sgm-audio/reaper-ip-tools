from reaper_assets import markers as M


def test_marker_line_format():
    line = M.marker_line(1, 0.0, "Session Start")
    assert line.startswith('MARKER 1 0 "Session Start" 0 255 1 R {')
    assert line.endswith("0 2")


def test_region_line_appends_end():
    line = M.marker_line(1, 0.0, "Intro", region_end=60.0)
    assert line.endswith("0 2 60")


def test_region_fractional_end():
    line = M.marker_line(1, 0.0, "Intro", region_end=30.5)
    assert line.endswith("0 2 30.5")


def test_write_marker_and_region_into_builder():
    from reaper_assets import builder as B

    b = B.ReaperProjectBuilder()
    M.write_marker(b, 1, 0.0, "Start")
    M.write_region(b, 2, 0.0, 30.0, "Verse")
    text = b.build()
    assert 'MARKER 1 0 "Start"' in text
    assert 'MARKER 2 0 "Verse"' in text
