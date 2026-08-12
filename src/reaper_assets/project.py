"""High-level RPP assembly from a declarative project spec."""

import os
import time

from . import builder as B
from . import markers as M
from . import routing as R
from .version import detect_reaper_version

__all__ = ["generate_rpp_project", "generate_rpp_string", "write_settings"]


def _norm_track(spec):
    """Accept a track as a bare name or a dict; return a normalized dict."""
    if isinstance(spec, str):
        return {"name": spec}
    return dict(spec)


def _build_receives(tracks, routes):
    """Resolve routes into AUXRECV lines keyed by destination track index."""
    index = {t["name"]: i for i, t in enumerate(tracks)}
    receives = {i: [] for i in range(len(tracks))}
    for route in routes:
        src = route["from"]
        dst = route["to"]
        if src not in index or dst not in index:
            raise KeyError(f"route references unknown track: {src!r} -> {dst!r}")
        mode = route.get("mode", 0)
        volume = route.get("volume", 0)
        line = R.auxrecv_line(index[src], mode=mode, volume=volume)
        receives[index[dst]].append(line)
    return receives


def write_settings(b, sample_rate=48000, bpm=120, time_sig=(4, 4), notes=None):
    """Emit canonical project settings + master + envelopes."""
    b.open("NOTES", 0, 2)
    for line in notes or []:
        b.prop(f"|{line}")
    b.close()

    b.prop("RIPPLE", 0, 0)
    b.prop("GROUPOVERRIDE", 0, 0, 0)
    b.prop("AUTOXFADE", 129)
    b.prop("ENVATTACH", 3)
    b.prop("POOLEDENVATTACH", 0)
    b.prop("MIXERUIFLAGS", 11, 48)
    b.prop("PEAKGAIN", 1)
    b.prop("FEEDBACK", 0)
    b.prop("PANLAW", 1)
    b.prop("PROJOFFS", 0, 0, 0)
    b.prop("MAXPROJLEN", 0, 600)
    b.prop("GRID", 3199, 8, 1, 8, 1, 0, 0, 0)
    b.prop("TIMEMODE", 1, 5, -1, 30, 0, 0, -1)
    b.prop("VIDEO_CONFIG", 0, 0, 256)
    b.prop("PANMODE", 3)
    b.prop("CURSOR", 0)
    b.prop("ZOOM", 100, 0, 0)
    b.prop("VZOOMEX", 6, 0)
    b.prop("USE_REC_CFG", 0)
    b.prop("RECMODE", 1)
    b.prop("SMPTESYNC", 0, 30, 100, 40, 1000, 300, 0, 0, 1, 0, 0)
    b.prop("LOOP", 0)
    b.prop("LOOPGRAN", 0, 4)
    b.prop("RECORD_PATH", '""', '""')
    b.open("RECORD_CFG")
    b.close()
    b.open("APPLYFX_CFG")
    b.close()
    b.prop("RENDER_FILE", '""')
    b.prop("RENDER_PATTERN", '""')
    b.prop("RENDER_FMT", 0, 2, 0)
    b.prop("RENDER_1X", 0)
    b.prop("RENDER_RANGE", 1, 0, 0, 18, 1000)
    b.prop("RENDER_RESAMPLE", 3, 0, 1)
    b.prop("RENDER_ADDTOPROJ", 0)
    b.prop("RENDER_STEMS", 0)
    b.prop("RENDER_DITHER", 0)
    b.prop("TIMELOCKMODE", 1)
    b.prop("TEMPOENVLOCKMODE", 1)
    b.prop("ITEMMIX", 1)
    b.prop("DEFPITCHMODE", 589824, 0)
    b.prop("TAKELANE", 1)
    b.prop("SAMPLERATE", sample_rate, 0, 0)
    b.open("RENDER_CFG")
    b.close()
    b.prop("LOCK", 1)

    b.open("METRONOME", 6, 0)
    b.prop("VOL", 0.25, 0.125)
    b.prop("BEATLEN", 4)
    b.prop("FREQ", 800, 1600, 1)
    b.prop("SAMPLES", '""', '""', '""', '""')
    b.prop("PATTERN", 0, 169)
    b.prop("PATTERNSTR", "ABBB")
    b.prop("MULT", 1)
    b.close()

    b.prop("GLOBAL_AUTO", -1)
    b.prop("TEMPO", bpm, time_sig[0], time_sig[1], 0)
    b.prop("PLAYRATE", 1, 0, 0.25, 4)
    b.prop("SELECTION", 0, 0)
    b.prop("SELECTION2", 0, 0)

    B.write_master(b)
    B.write_envelope(b, "MASTERPLAYSPEEDENV", active=0, vis=(0, 1, 1), defshape=0)
    B.write_envelope(b, "TEMPOENVEX", active=0, vis=(1, 0, 1), defshape=1)

    b.open("PROJBAY")
    b.close()


def generate_rpp_string(spec):
    """Assemble a full RPP document string from a project spec dict.

    spec keys (all optional unless noted):
      sample_rate, bpm, time_sig, notes, version,
      tracks (list of name-or-dict; dict keys: name, color, folder, fx),
      routes (list of {from, to, mode?, volume?}),
      markers (list of {pos, name, color?}),
      regions (list of {start, end, name, color?})
    """
    tracks = [_norm_track(t) for t in spec.get("tracks", [])]
    routes = spec.get("routes", [])
    receives = _build_receives(tracks, routes)

    b = B.ReaperProjectBuilder()
    version = spec.get("version") or detect_reaper_version()
    B.project_header(b, version, timestamp=spec.get("timestamp") or int(time.time()))

    write_settings(
        b,
        sample_rate=spec.get("sample_rate", 48000),
        bpm=spec.get("bpm", 120),
        time_sig=spec.get("time_sig", (4, 4)),
        notes=spec.get("notes"),
    )

    for i, t in enumerate(tracks):
        B.write_track(
            b,
            t["name"],
            color=t.get("color"),
            folder=t.get("folder"),
            receives=receives.get(i),
            fx=t.get("fx") or [],
            mainsends=t.get("mainsends", 1),
        )

    idx = 1
    for m in spec.get("markers", []):
        M.write_marker(b, idx, m["pos"], m["name"], color=m.get("color", 255))
        idx += 1
    for r in spec.get("regions", []):
        M.write_region(
            b, idx, r["start"], r["end"], r["name"], color=r.get("color", 255)
        )
        idx += 1

    b.open("EXTENSIONS")
    b.close()

    b.close()  # REAPER_PROJECT
    return b.build()


def generate_rpp_project(output_path, spec):
    """Write a full RPP project to ``output_path``; returns the text."""
    text = generate_rpp_string(spec)
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text
