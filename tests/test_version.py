"""Tests for reaper_assets.version (REAPER version detection)."""

import os

from reaper_assets import version as V


def test_detect_reaper_version_pairs_newest_with_own_platform(tmp_path):
    # Alphabetically, z_old.rpp comes AFTER a_new.rpp; platform must match a_new.rpp!
    (tmp_path / "a_new.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.69/linux-x86_64" 1\n>\n', encoding="utf-8"
    )
    (tmp_path / "z_old.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.38/win64" 1\n>\n', encoding="utf-8"
    )
    assert V.detect_reaper_version(str(tmp_path)) == "7.69/linux-x86_64"


def test_detect_reaper_version_preserves_leading_zero_minor_and_suffixes(tmp_path):
    (tmp_path / "t1.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.05/win64" 1\n>\n', encoding="utf-8"
    )
    assert V.detect_reaper_version(str(tmp_path)) == "7.05/win64"

    (tmp_path / "t2.RPP").write_text(
        '<REAPER_PROJECT 0.1 "7.12.1/OSX64" 1\n>\n', encoding="utf-8"
    )
    assert V.detect_reaper_version(str(tmp_path)) == "7.12.1/OSX64"

    (tmp_path / "t3.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.70+dev0401/linux-x86_64" 1\n>\n', encoding="utf-8"
    )
    assert V.detect_reaper_version(str(tmp_path)) == "7.70+dev0401/linux-x86_64"


def test_detect_reaper_version_checks_project_templates_subdir(tmp_path):
    sub = tmp_path / "Project Templates"
    sub.mkdir()
    (sub / "template.rpp").write_text(
        '<REAPER_PROJECT 0.1 "7.57/win64" 1\n>\n', encoding="utf-8"
    )
    assert V.detect_reaper_version(str(tmp_path)) == "7.57/win64"


def test_detect_reaper_version_fallback_on_missing_or_empty(tmp_path):
    assert V.detect_reaper_version(str(tmp_path / "missing")) == V.DEFAULT_VERSION
    assert V.detect_reaper_version(str(tmp_path)) == V.DEFAULT_VERSION


def test_resource_path_darwin_and_linux(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(V.os, "name", "posix")

    monkeypatch.setattr(V.sys, "platform", "darwin")
    assert V._resource_path().endswith(
        os.path.join("Library", "Application Support", "REAPER")
    )

    monkeypatch.setattr(V.sys, "platform", "linux")
    assert V._resource_path().endswith(os.path.join(".config", "REAPER"))
