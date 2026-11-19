import os
import re

import pytest

from reaper_assets import builder as B

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
_GUID_RE = re.compile(
    r"^\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}$"
)


def test_color_to_native_packs_rgb_and_flag():
    assert B.color_to_native(255, 0, 0) == (255 | (0 << 8) | (0 << 16)) | 0x1000000
    assert B.color_to_native(0, 255, 0) == (255 << 8) | 0x1000000
    assert B.color_to_native(0, 0, 255) == (255 << 16) | 0x1000000
    assert B.color_to_native(0, 0, 0) == 0x1000000


def test_color_to_native_rejects_out_of_range():
    with pytest.raises(ValueError):
        B.color_to_native(256, 0, 0)
    with pytest.raises(ValueError):
        B.color_to_native(0, -1, 0)
    with pytest.raises(ValueError):
        B.color_to_native(0, 0, 999)


def test_rpp_quote_delimiters_and_newline_rejection():
    assert B.rpp_quote("Kick") == '"Kick"'
    assert B.rpp_quote('Say "Hi"') == "'Say \"Hi\"'"
    assert B.rpp_quote("Bob's \"Mix\"") == "`Bob's \"Mix\"`"
    assert B.rpp_quote('a "b" \'c\' `d`') == "`a \"b\" 'c' 'd'`"
    assert B.rpp_quote("", prefer="'") == "''"
    assert B.rpp_quote("Bob's", prefer="'") == '"Bob\'s"'
    with pytest.raises(ValueError):
        B.rpp_quote("line1\nline2")
    with pytest.raises(ValueError):
        B.rpp_quote("line1\rline2")


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


def test_write_envelope_emits_hyphenated_eguid():
    b = B.ReaperProjectBuilder()
    B.write_envelope(b, "TEMPOENVEX")
    lines = [line.strip() for line in b.build().splitlines()]
    eguid_line = next(line for line in lines if line.startswith("EGUID "))
    guid = eguid_line.split()[1]
    assert _GUID_RE.match(guid), f"EGUID not hyphenated: {guid}"


def test_write_track_emits_canonical_lines():
    b = B.ReaperProjectBuilder()
    B.write_track(b, "Kick", color=(255, 68, 68))
    text = b.build()
    lines = text.splitlines()

    assert lines[0].startswith("<TRACK {")
    stripped = [line.strip() for line in lines]
    assert 'NAME "Kick"' in stripped
    assert "VOLPAN 1 0 -1 -1 1" in stripped
    assert "MUTESOLO 0 0 0" in stripped
    assert "ISBUS 0 0" in stripped
    assert "MAINSEND 1 0" in stripped
    assert "FX 1" in stripped
    # TRACKID matches the TRACK guid and is hyphenated
    guid = lines[0].split()[1]
    assert _GUID_RE.match(guid)
    assert f"TRACKID {guid}" in stripped


def test_write_track_fx_boolean_mute_guid_and_quoting():
    b = B.ReaperProjectBuilder()
    B.write_track(
        b,
        'Lead "Vox"',
        fx=["ReaGate", "ReaEQ", "ReaComp"],
        track_guid="{11111111-2222-4333-8444-555555555555}",
        mute=True,
        fx_enabled=True,
    )
    text = b.build()
    stripped = [line.strip() for line in text.splitlines()]
    assert "<TRACK {11111111-2222-4333-8444-555555555555}" in stripped
    assert "TRACKID {11111111-2222-4333-8444-555555555555}" in stripped
    assert "{{11111111" not in text
    assert "NAME 'Lead \"Vox\"'" in stripped
    assert "MUTESOLO 1 0 0" in stripped
    # FX is a boolean enable flag (1), NOT len(fx) (3)
    assert "FX 1" in stripped
    assert "FX 3" not in stripped

    b2 = B.ReaperProjectBuilder()
    B.write_track(b2, "Bypassed", fx_enabled=False)
    assert "FX 0" in [line.strip() for line in b2.build().splitlines()]


def test_project_header_preserves_zero_timestamp():
    b = B.ReaperProjectBuilder()
    B.project_header(b, "7.0/win64", timestamp=0)
    b.close()
    assert b.build().splitlines()[0] == '<REAPER_PROJECT 0.1 "7.0/win64" 0'


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
