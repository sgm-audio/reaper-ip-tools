"""REAPER version detection.

Determines the ``"X.YY/win64"`` header string by scanning the installed
Project Templates for the highest version REAPER has written, falling back to
a sensible default when nothing is found.
"""

import glob
import os
import re

DEFAULT_VERSION = "7.0/win64"

_HEADER_RE = re.compile(r'<REAPER_PROJECT 0\.1 "(\d+\.\d+)/([^"]+)"')


def _resource_path():
    env = os.environ.get("APPDATA")
    if env:
        return os.path.join(env, "REAPER")
    home = os.path.expanduser("~")
    if os.name == "nt":
        return os.path.join(home, "AppData", "Roaming", "REAPER")
    if os.name == "darwin":
        return os.path.expanduser("~/Library/Application Support/REAPER")
    return os.path.expanduser("~/.config/REAPER")


def _template_dir():
    return os.path.join(_resource_path(), "Project Templates")


def detect_reaper_version(resource_path=None):
    """Return a ``"X.YY/win64"`` version string.

    Scans ``<REAPER_PROJECT ... "X.YY/win64" ...>`` headers in the Project
    Templates directory (or ``resource_path``), returning the newest version.
    Falls back to ``DEFAULT_VERSION``.
    """
    root = resource_path or _template_dir()
    if not root or not os.path.isdir(root):
        return DEFAULT_VERSION

    versions = []
    platform = "win64"
    for path in glob.glob(os.path.join(root, "*.rpp")) + glob.glob(
        os.path.join(root, "*.RPP")
    ):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.readline()
        except OSError:
            continue
        m = _HEADER_RE.search(head)
        if m:
            versions.append(tuple(int(x) for x in m.group(1).split(".")))
            platform = m.group(2)

    if not versions:
        return DEFAULT_VERSION
    newest = max(versions)
    return ".".join(str(x) for x in newest) + "/" + platform
