# Podcast Session Template — Session Map

## Assumptions
- **Target REAPER version:** 7.x, 64-bit Windows (macOS/Linux compatible; no OS-specific chunks used).
- **Workflow:** Podcast / dialogue production — up to 3 co-hosts + music bed + SFX.
- **Approach:** `template.RPP` is a minimal, valid project shell. All track/bus/routing/FX/marker construction happens in `bootstrap.lua` via the REAPER API, so no GUIDs, FX state blobs, or uncertain RPP chunks are hand-authored.
- **FX strategy:** Stock REAPER plugins only (`ReaGate`, `ReaEQ`, `ReaComp`, `ReaLimit`), script-added at default parameters. No third-party plugin UIDs are referenced.
- **Loudness target:** -16 LUFS integrated (podcast standard), 48 kHz / 24-bit WAV.

## Architecture overview

```
SHOW_MASTER (bus)  ────────────────► Master (hardware)
   ▲          ▲          ▲
   │          │          │
DIALOGUE_BUS  MUSIC_BED  SFX_LIB
   ▲
   ├── SPKF_DALE
   ├── SPKF_JAMIE
   └── SPKF_BRIAN
```

- **Two-stage bus topology:** per-speaker tracks feed a `DIALOGUE_BUS` (where all
  dialogue processing lives), which then feeds `SHOW_MASTER`. Music and SFX bypass the
  dialogue bus and feed `SHOW_MASTER` directly.
- **Master-send discipline:** only `SHOW_MASTER` has master/parent send enabled; every
  other track routes through an explicit send. This prevents double-routing.

## Track layout (top → bottom)

| # | Track | Type | Color | FX (script-added) |
|---|---|---|---|---|
| 1 | SHOW_MASTER | bus | white `#FFFFFF` | ReaComp, ReaLimit |
| 2 | DIALOGUE_BUS | bus | red `#FF5252` | ReaGate, ReaEQ, ReaComp |
| 3 | SPKF_DALE | source | rust `#E85D3F` | — |
| 4 | SPKF_JAMIE | source | blue `#3FA7E8` | — |
| 5 | SPKF_BRIAN | source | green `#7ADB62` | — |
| 6 | MUSIC_BED | source | purple `#C792EA` | — |
| 7 | SFX_LIB | source | yellow `#F4D35E` | — |

## Naming convention
- Speaker tracks: `SPKF_<NAME>` (uppercase, underscore).
- Buses: `DIALOGUE_BUS`, `SHOW_MASTER`.
- Source beds: `MUSIC_BED`, `SFX_LIB`.

## Color strategy
- **By function:** buses are high-signal colors (white = final, red = dialogue).
- **Per-speaker:** each speaker gets a distinct hue so waveform lanes and mixer strips are
  instantly distinguishable.

## Markers & regions
- Markers: `Show Start` (0s), `Main Content` (60s), `Outro Start` (300s).
- Regions: `COLD OPEN` (0–60s), `MAIN SEGMENT` (60–300s), `OUTRO` (300–330s).

## Gain staging policy
- Source tracks (speakers, music, SFX): target peaks around **-18 dBFS** (record/trim before processing).
- `DIALOGUE_BUS`: leave ~6 dB headroom post-compressor for loudness at show bus.
- `SHOW_MASTER`: final stage targets **-16 LUFS** with peaks ≤ **-1.0 dBTP** via `ReaLimit`.

## FX chains (script-generated, stock only, default params)
- **DIALOGUE_BUS:** `ReaGate` (breath/room floor) → `ReaEQ` (low cut ~80 Hz, presence) → `ReaComp` (level control). *Tune per voice.*
- **SHOW_MASTER:** `ReaComp` (glue) → `ReaLimit` (true-peak ceiling). *Set ceiling to -1.0 dB.*
- Per-speaker de-noising/de-essing is intentionally left to the user (third-party RX-style tools); add as needed.
