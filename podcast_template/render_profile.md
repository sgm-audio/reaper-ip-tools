# Podcast Session Template — Render Profile

## Primary master render

| Setting | Value |
|---|---|
| Format | WAV |
| Sample rate | 48,000 Hz |
| Bit depth | 24-bit PCM |
| Channels | Stereo (or Mono — see note) |
| Time selection | Entire project (respect region selection if using regions) |
| Loudness target | **-16 LUFS** integrated |
| True-peak ceiling | **-1.0 dBTP** |
| Normalization | Off during render (reach loudness via SHOW_MASTER chain) |

## Stem / alternate renders (optional)

| Stem | Source | Purpose |
|---|---|---|
| Dialogue stem | DIALOGUE_BUS (solo) | re-purposing, clips, localization |
| Music + SFX stem | MUSIC_BED + SFX_LIB (solo) | scoring swaps, licensed music replacement |
| Full mix | SHOW_MASTER | distribution |

## Loudness workflow
1. Mix/trim sources to ~-18 dBFS peaks.
2. Set `ReaLimit` ceiling to **-1.0 dB** on SHOW_MASTER.
3. Measure integrated loudness (e.g. `SWS/BR: Analyze loudness` or REAPER's
   **Stats** — `File > Render` with "Normalize to -16 LUFS" as a final safety pass).
4. Adjust SHOW_MASTER gain so integrated loudness lands at **-16 LUFS ± 0.5**.

## Platform quick reference

| Destination | LUFS target |
|---|---|
| Podcast RSS / Apple Podcasts | -16 LUFS |
| Spotify (podcast) | -14 LUFS (streaming) |
| YouTube (video companion) | -14 LUFS |
| Broadcast | -23 LUFS |

> Default template is authored for **-16 LUFS** (podcast standard). Adjust
> `ReaLimit`/gain for other targets.
