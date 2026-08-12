import os

import pytest

from reaper_assets import builder as B

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_color_to_native_packs_rgb_and_flag():
    assert B.color_to_native(255, 0, 0) == (255 | (0 << 8) | (0 << 16)) | 0x1000000
    assert B.color_to_native(0, 255, 0) == (255 << 8) | 0x1000000
    assert B.color_to_native(0, 0, 255) == (255 << 16) | 0x1000000


def test_builder_balanced():
    b = B.ReaperProjectBuilder()
    b.open("TRACK", "{GUID}")
    b.prop("NAME", '"X"')
    b.close()
    assert b.build() == '<TRACK {GUID}\n  NAME "X"\n>\n'


def test_builder_rejects_unbalanced():
    b = B.ReaperProjectBuilder()
    b.open("TRACK", "{GUID}")
    with pytest.raises(ValueError):
        b.build()


def test_write_track_emits_canonical_lines():
    b = B.ReaperProjectBuilder()
    B.write_track(b, "Kick", color=(255, 68, 68))
    text = b.build()
    lines = text.splitlines()

    assert lines[0].startswith("<TRACK {")
    stripped = [l.strip() for l in lines]
    assert 'NAME "Kick"' in stripped
    assert "VOLPAN 1 0 -1 -1 1" in stripped
    assert "ISBUS 0 0" in stripped
    assert "MAINSEND 1 0" in stripped
    assert "FX 0" in stripped
    # TRACKID matches the TRACK guid
    guid = lines[0].split()[1]
    assert f"TRACKID {guid}" in stripped


def _track_field_names(text):
    """Extract track-level field names from a track block, indentation-agnostic."""
    fields = set()
    in_track = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("<TRACK"):
            in_track = True
            continue
        if not in_track:
            continue
        if s.startswith("<"):
            break  # hit <FXCHAIN (or another node)
        if s and not s.startswith(">"):
            fields.add(s.split()[0])
    return fields


def test_write_track_golden_against_fixture():
    """Field set matches REAPER's canonical track block (voice_over.rpp)."""
    with open(os.path.join(FIXTURES, "voice_over.rpp"), encoding="utf-8") as f:
        fixture = f.read()

    fixture_fields = _track_field_names(fixture)

    b = B.ReaperProjectBuilder()
    B.write_track(b, "Voice")
    generated_fields = _track_field_names(b.build())

    assert fixture_fields, "failed to parse fixture track fields"
    assert fixture_fields <= generated_fields, (
        f"missing fields vs REAPER: {fixture_fields - generated_fields}"
    )
    assert "<FXCHAIN" in b.build()


def test_write_track_mainsends_bus():
    b = B.ReaperProjectBuilder()
    B.write_track(b, "BUS", mainsends=0)
    assert "MAINSEND 0 0" in b.build()
