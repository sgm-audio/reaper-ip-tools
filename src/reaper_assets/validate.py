"""Validation: structural RPP checks plus optional REAPER round-trip.

Structural checks always run and are cheap. The REAPER round-trip check is
opt-in and requires a REAPER install; it renders the project headlessly and
treats a clean exit as proof that REAPER parsed the file.
"""

import os
import shutil
import subprocess
import tempfile

__all__ = [
    "find_reaper_exe",
    "roundtrip_check",
    "validate_rpp",
    "validate_rpp_file",
]

_QUOTED_NUMERIC = ('VOLPAN "', 'TEMPO "', 'SAMPLERATE "', 'MAINSEND "', 'ISBUS "')


def validate_rpp(text):
    """Return a list of structural problems in ``text`` (empty = valid)."""
    errors = []
    lines = text.splitlines()
    if not lines or not lines[0].startswith("<REAPER_PROJECT"):
        errors.append("first line is not <REAPER_PROJECT")
    if text.strip().splitlines()[-1] != ">":
        errors.append("file does not end with a closing '>'")

    depth = 0
    for ln in lines:
        stripped = ln.lstrip()
        opens = stripped.startswith("<")
        closes = stripped.rstrip().endswith(">")
        depth += (1 if opens else 0) - (1 if closes else 0)
        if depth < 0:
            errors.append("unbalanced closing '>'")
            break
    if depth != 0:
        errors.append(f"unbalanced node nesting (depth {depth})")

    for bad in _QUOTED_NUMERIC:
        if bad in text:
            errors.append(f"quoted numeric field found: {bad}")
    return errors


def validate_rpp_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return validate_rpp(f.read())


def find_reaper_exe():
    """Locate ``reaper.exe`` on Windows, or return None."""
    if os.name != "nt":
        return None
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "REAPER (x64)", "reaper.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "REAPER", "reaper.exe"),
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Programs", "REAPER (x64)", "reaper.exe"
        ),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def roundtrip_check(rpp_path, reaper_exe=None, timeout=300):
    """Load ``rpp_path`` in REAPER headlessly and report whether it parses.

    Returns ``(ok, message)``. ``ok`` is True on a clean render, False on a
    hard failure, and None when REAPER is unavailable (not an error).

    Uses ``reaper.exe -nosplash -renderproject``. The 300s default accounts
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
        # Point the render at a concrete file. Do NOT alter RENDER_RANGE — the
        # canonical `1 0 0 18 1000` renders fine, while a rewritten range can
        # make REAPER block.
        text = text.replace('RENDER_FILE ""', f'RENDER_FILE "{out_wav}"')
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
