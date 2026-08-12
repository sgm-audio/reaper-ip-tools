# Podcast Session Template — Routing Matrix

## Signal flow

| Source track | Send target | Master/parent send | Purpose |
|---|---|---|---|
| SPKF_DALE | DIALOGUE_BUS | disabled | co-host 1 → dialogue processing |
| SPKF_JAMIE | DIALOGUE_BUS | disabled | co-host 2 → dialogue processing |
| SPKF_BRIAN | DIALOGUE_BUS | disabled | co-host 3 → dialogue processing |
| DIALOGUE_BUS | SHOW_MASTER | disabled | processed dialogue → final bus |
| MUSIC_BED | SHOW_MASTER | disabled | music bed → final bus (bypasses dialogue chain) |
| SFX_LIB | SHOW_MASTER | disabled | SFX → final bus (bypasses dialogue chain) |
| SHOW_MASTER | Master | **enabled** | final mix → hardware output |

## Bus / folder semantics

| Bus | Receives from | Sends to | Role |
|---|---|---|---|
| DIALOGUE_BUS | all `SPKF_*` tracks | SHOW_MASTER | gate + EQ + compression for voices |
| SHOW_MASTER | DIALOGUE_BUS, MUSIC_BED, SFX_LIB | Master | glue compression + true-peak limiting |

## Send defaults
- All sends are created as **post-fader** sends at unity gain (REAPER default).
- Pan follows source; bus receives are stereo.
- No VCA groups are created (single-operator podcast mix; VCAs optional for larger shows).

## Notes
- Routing is created idempotently by `bootstrap.lua` via `reaper.CreateTrackSend`; existing
  sends are detected and not duplicated.
- To add a speaker: add a `{name, rgb, bus="source"}` entry to `CONFIG.tracks` and a
  `{from = "<name>", to = "DIALOGUE_BUS"}` entry to `CONFIG.routes`, then re-run.
