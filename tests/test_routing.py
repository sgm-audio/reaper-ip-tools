from reaper_assets import routing as R


def test_auxrecv_line_format_matches_reaper():
    # Ground truth from Death Metal.rpp: AUXRECV 7 0 1 0 0 0 0 0 0 -1:U 0 -1 ''
    line = R.auxrecv_line(7, mode=1)
    assert line == "AUXRECV 7 0 1 0 0 0 0 0 0 -1:U 0 -1 ''"


def test_auxrecv_default_mode_zero():
    assert R.auxrecv_line(4) == "AUXRECV 4 0 0 0 0 0 0 0 0 -1:U 0 -1 ''"


def test_isbus_parent_child_end():
    assert R.isbus_value(R.FOLDER_PARENT) == (1, 1)
    assert R.isbus_value(R.FOLDER_CHILD) == (0, 0)
    assert R.isbus_value(R.FOLDER_END) == (2, -1)
    assert R.isbus_value(None) == (0, 0)
