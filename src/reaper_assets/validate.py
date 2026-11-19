"""Validation: structural RPP checks plus optional REAPER round-trip.

Structural checks always run and are cheap. The REAPER round-trip check is
opt-in and requires a REAPER install; it renders the project headlessly and
treats a clean exit as proof that REAPER parsed the file.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

from .builder import rpp_quote

__all__ = [
    "find_reaper_exe",
    "roundtrip_check",
    "validate_rpp",
    "validate_rpp_file",
]

_QUOTED_NUMERIC_RE = re.compile(
    r'^\s*(VOLPAN|TEMPO|SAMPLERATE|MAINSEND|ISBUS)\s+"', re.MULTILINE
)
_RENDER_FILE_RE = re.compile(r"^([ \t]*RENDER_FILE)[ \t]+.*$", re.MULTILINE)


def validate_rpp(text):
    """Return a list of structural problems in ``text`` (empty = valid)."""
    errors = []
    stripped_lines = text.strip().splitlines()
    if not stripped_lines:
        return ["empty RPP document"]

    lines = text.splitlines()
    if not lines or not lines[0].startswith("<REAPER_PROJECT"):
        errors.append("first line is not <REAPER_PROJECT")
    if stripped_lines[-1].strip() != ">":
        errors.append("file does not end with a closing '>'")

    depth = 0
    for ln in lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("|"):
            continue
        if stripped.startswith("<"):
            depth += 1
        elif stripped == ">":
            depth -= 1
            if depth < 0:
                errors.append("unbalanced closing '>'")
                break
    if depth != 0:
        errors.append(f"unbalanced node nesting (depth {depth})")

    for m in _QUOTED_NUMERIC_RE.finditer(text):
        errors.append(f'quoted numeric field found: {m.group(1)} "')
    return errors


def validate_rpp_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return validate_rpp(f.read())


def find_reaper_exe():
    """Locate the REAPER executable across Windows, macOS, and Linux, or return None."""
    if os.name == "nt":
        candidates = []
        pf = os.environ.get("PROGRAMFILES")
        if pf:
            candidates.extend(
                [
                    os.path.join(pf, "REAPER (x64)", "reaper.exe"),
                    os.path.join(pf, "REAPER", "reaper.exe"),
                ]
            )
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(
                os.path.join(local, "Programs", "REAPER (x64)", "reaper.exe")
            )
        found = shutil.which("reaper.exe") or shutil.which("reaper")
        if found:
            candidates.append(found)
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/REAPER.app/Contents/MacOS/REAPER",
            os.path.expanduser("~/Applications/REAPER.app/Contents/MacOS/REAPER"),
        ]
        found = shutil.which("reaper")
        if found:
            candidates.append(found)
    else:
        candidates = []
        found = shutil.which("reaper")
        if found:
            candidates.append(found)
        candidates.extend(
            [
                "/usr/bin/reaper",
                "/usr/local/bin/reaper",
                "/opt/REAPER/reaper",
                os.path.expanduser("~/opt/REAPER/reaper"),
            ]
        )

    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _set_render_file(text, out_wav):
    """Replace any existing RENDER_FILE line with ``out_wav``, or insert one."""
    quoted = rpp_quote(out_wav)
    new_text, count = _RENDER_FILE_RE.subn(
        lambda m: f"{m.group(1)} {quoted}", text, count=1
    )
    if count > 0:
        return new_text
    lines = text.splitlines(keepends=True)
    if lines:
        lines.insert(1, f"  RENDER_FILE {quoted}\n")
        return "".join(lines)
    return text


def roundtrip_check(rpp_path, reaper_exe=None, timeout=300):
    """Load ``rpp_path`` in REAPER headlessly and report whether it parses.

    Returns ``(ok, message)``. ``ok`` is True on a clean render, False on a
    hard failure, and None when REAPER is unavailable (not an error).

    Uses ``reaper -nosplash -renderproject``. The 300s default accounts
    for a cold start (first-run VST scan can be slow).
    """
    exe = reaper_exe or find_reaper_exe()
    if not exe or not os.path.exists(exe):
        return None, "REAPER executable not found; skipping round-trip check"

    tmp = tempfile.mkdtemp(prefix="reaper_assets_rt_")
    try:
        out_wav = os.path.join(tmp, "out.wav")
        proj = os.path.join(tmp, "check.rpp")
        with open(rpp_path, "r", encoding="utf-8") as f:
            text = f.read()
        # Point the render at a concrete temp file. Do NOT alter RENDER_RANGE —
        # the canonical `1 0 0 18 1000` renders fine, while a rewritten range
        # can make REAPER block.
        text = _set_render_file(text, out_wav)
        with open(proj, "w", encoding="utf-8") as f:
            f.write(text)

        try:
            # Redirect to DEVNULL (not pipes) — REAPER holds pipe handles open
            # on Windows, which makes subprocess.run hang on EOF.
            proc = subprocess.run(
                [exe, "-nosplash", "-renderproject", proj],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "REAPER render timed out"
        except OSError as e:
            return False, f"failed to launch REAPER: {e}"

        rendered = os.path.exists(out_wav) and os.path.getsize(out_wav) > 0
        if rendered:
            # A rendered WAV is the real signal: REAPER parsed and processed
            # the project. Some multi-folder projects make REAPER crash during
            # teardown *after* a successful render (a REAPER headless quirk,
            # reproducible with the user's own templates), so a non-zero exit
            # is reported but not treated as project invalidity.
            if proc.returncode == 0:
                return True, f"REAPER loaded and rendered successfully ({exe})"
            return True, (
                f"REAPER rendered successfully, but exited {proc.returncode:#x} "
                f"during teardown (known REAPER headless quirk with multi-folder "
                f"projects) — project is valid"
            )
        return False, f"REAPER failed to render (exit {proc.returncode:#x})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
