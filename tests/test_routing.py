import pytest

from reaper_assets import routing as R


def test_auxrecv_line_format_matches_reaper():
    # REAPER format:
    # AUXRECV <src> <mode> <vol_linear> <pan> <mute> <mono> <phase> <src_ch> <dst_ch> <panlaw> <midi_flags> <automode> <name>
    line = R.auxrecv_line(7)
    assert line == "AUXRECV 7 0 1 0 0 0 0 0 0 -1:U 0 -1 ''"


def test_auxrecv_mode_volume_midi_flags_and_name():
    line = R.auxrecv_line(4, mode=3, volume=0.5, name="Verb", midi_flags=31)
    assert line == "AUXRECV 4 3 0.5 0 0 0 0 0 0 -1:U 31 -1 'Verb'"


def test_auxrecv_quotes_special_names():
    assert R.auxrecv_line(0, name="Bob's Send").endswith('"Bob\'s Send"')
    assert R.auxrecv_line(0, name='Bob\'s "Send"').endswith('`Bob\'s "Send"`')
    with pytest.raises(ValueError):
        R.auxrecv_line(0, name="bad\nname")


def test_isbus_parent_child_end_and_unknown():
    assert R.isbus_value(R.FOLDER_PARENT) == (1, 1)
    assert R.isbus_value(R.FOLDER_CHILD) == (0, 0)
    assert R.isbus_value(R.FOLDER_END) == (2, -1)
    assert R.isbus_value(None) == (0, 0)
    with pytest.raises(ValueError):
        R.isbus_value("unknown_role")
