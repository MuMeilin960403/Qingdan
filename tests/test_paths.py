from __future__ import annotations

from pathlib import Path

import pytest

from qingdan import paths


def test_env_override_is_used_and_created(tmp_path, monkeypatch):
    custom = tmp_path / "custom-qingdan-data"
    monkeypatch.setenv("QINGDAN_DATA_DIR", str(custom))
    monkeypatch.setattr(paths, "_CACHED_DATA_DIR", None)

    resolved = paths.resolve_data_dir()
    assert resolved == custom.resolve()
    assert custom.is_dir()
    assert paths.app_data_dir() == custom.resolve()
    assert paths.tasks_path() == custom.resolve() / "tasks.json"


def test_resolver_falls_back_to_a_writable_candidate(tmp_path, monkeypatch):
    bad = tmp_path / "blocked"
    good = tmp_path / "writable"
    good.mkdir()
    monkeypatch.setattr(paths, "candidate_data_dirs", lambda: [bad, good])
    monkeypatch.setattr(paths, "_is_writable", lambda candidate: candidate == good)

    assert paths.resolve_data_dir() == good


def test_resolver_reports_all_failed_candidates(tmp_path, monkeypatch):
    candidates = [tmp_path / "one", tmp_path / "two"]
    monkeypatch.setattr(paths, "candidate_data_dirs", lambda: candidates)
    monkeypatch.setattr(paths, "_is_writable", lambda candidate: False)

    with pytest.raises(paths.DataDirectoryError) as exc_info:
        paths.resolve_data_dir()
    assert "QINGDAN_DATA_DIR" in str(exc_info.value)
    assert str(candidates[0]) in str(exc_info.value)
    assert str(candidates[1]) in str(exc_info.value)


def test_application_dir_for_source_is_project_root(monkeypatch):
    monkeypatch.delenv("QINGDAN_DATA_DIR", raising=False)
    assert paths.application_dir() == paths.project_root()
    assert paths.candidate_data_dirs()[0] == paths.project_root() / "data"
