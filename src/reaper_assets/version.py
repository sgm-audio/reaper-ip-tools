"""REAPER version detection.

Determines the ``"X.YY/win64"`` header string by scanning the installed
Project Templates for the highest version REAPER has written, falling back to
a sensible default when nothing is found.
"""

import os
import re
import sys

DEFAULT_VERSION = "7.0/win64"

_HEADER_RE = re.compile(r'<REAPER_PROJECT\s+0\.1\s+"(\d+(?:\.\d+)+[^"/]*)/([^"]+)"')
_NUM_PREFIX_RE = re.compile(r"(\d+(?:\.\d+)+)")


def _resource_path():
    env = os.environ.get("APPDATA")
    if env:
        return os.path.join(env, "REAPER")
    home = os.path.expanduser("~")
    if os.name == "nt":
        return os.path.join(home, "AppData", "Roaming", "REAPER")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/REAPER")
    return os.path.expanduser("~/.config/REAPER")


def _template_dir():
    return os.path.join(_resource_path(), "Project Templates")


def detect_reaper_version(resource_path=None):
    """Return a ``"X.YY/platform"`` version string.

    Scans ``<REAPER_PROJECT ... "X.YY/platform" ...>`` headers in the Project
    Templates directory (or ``resource_path``, plus its ``Project Templates``
    subdirectory when present), returning the newest version paired with its
    platform. Falls back to ``DEFAULT_VERSION``.
    """
    root = resource_path or _template_dir()
    if not root or not os.path.isdir(root):
        return DEFAULT_VERSION

    scan_dirs = [root]
    sub = os.path.join(root, "Project Templates")
    if os.path.isdir(sub):
        scan_dirs.append(sub)

    candidates = []
    for directory in scan_dirs:
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            continue
        for fn in entries:
            if not fn.lower().endswith(".rpp"):
                continue
            path = os.path.join(directory, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    head = f.readline()
            except OSError:
                continue
            m = _HEADER_RE.search(head)
            if m:
                raw_ver, platform = m.group(1), m.group(2)
                num_m = _NUM_PREFIX_RE.match(raw_ver)
                if not num_m:
                    continue
                ver_tuple = tuple(int(x) for x in num_m.group(1).split("."))
                candidates.append((ver_tuple, raw_ver, platform))

    if not candidates:
        return DEFAULT_VERSION
    _, newest_raw, newest_platform = max(candidates, key=lambda c: c[0])
    return f"{newest_raw}/{newest_platform}"
