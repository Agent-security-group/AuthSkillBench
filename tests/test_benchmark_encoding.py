"""Tests for benchmark.read_json JSON loading.

Covers: UTF-8 file loading, real task file loading, and edge cases.
Originally the data files are all UTF-8 encoded.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scenarios.browser.app.benchmark import read_json


def _write_file(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode(encoding))


class TestReadJsonUtf8:
    """Standard UTF-8 files must load correctly."""

    def test_utf8_file(self, tmp_path: Path):
        data = {"task_type": "normal_authorized", "description": "API文档"}
        p = tmp_path / "task.json"
        _write_file(p, json.dumps(data, ensure_ascii=False), "utf-8")
        assert read_json(p) == data

    def test_utf8_with_chinese(self, tmp_path: Path):
        data = {"operation": "api_call", "说明": "检查内部服务健康状态"}
        p = tmp_path / "task_cn.json"
        _write_file(p, json.dumps(data, ensure_ascii=False), "utf-8")
        assert read_json(p) == data


class TestReadJsonRealTaskFiles:
    """All real task JSON files under data/tasks must be loadable as UTF-8."""

    @pytest.fixture(scope="class")
    def tasks_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "scenarios" / "browser" / "data" / "tasks"

    def test_all_task_files_loadable(self, tasks_dir: Path):
        files = list(tasks_dir.rglob("*.json"))
        assert len(files) > 0, "Expected task JSON files to exist"
        for f in files:
            data = read_json(f)
            assert isinstance(data, dict), f"{f} did not decode to a dict"
            assert "task_type" in data or "operation" in data, f"{f} missing expected keys"

    def test_navigate_internal_has_chinese(self, tasks_dir: Path):
        """navigate_internal.json must have readable Chinese description."""
        p = tasks_dir / "browser_automation" / "navigate_internal.json"
        assert p.exists()
        data = read_json(p)
        desc = data.get("description", "")
        assert "导航" in desc, f"Expected Chinese text in description, got: {desc}"

    def test_no_mojibake_in_any_file(self, tasks_dir: Path):
        """No file should contain GBK-as-UTF8 mojibake artifacts.

        These characters only appear when UTF-8 bytes are misdecoded as GBK.
        They are extremely rare in normal Chinese text.
        """
        # True mojibake chars (rare CJK that only appear from UTF-8-as-GBK decoding)
        mojibake_chars = ["鍦", "鐢", "叕", "鍙", "唴", "缃", "郴", "缁", "熶", "瀵", "埅", "鍒"]
        for f in tasks_dir.rglob("*.json"):
            text = f.read_text(encoding="utf-8")
            for mc in mojibake_chars:
                assert mc not in text, f"Mojibake character '{mc}' found in {f}"


class TestReadJsonEdgeCases:
    """Edge cases for read_json."""

    def test_empty_json_object(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        _write_file(p, "{}", "utf-8")
        assert read_json(p) == {}

    def test_json_with_nested_arrays(self, tmp_path: Path):
        data = {"preconditions": ["a", "b"], "nested": {"key": ["v1", "v2"]}}
        p = tmp_path / "nested.json"
        _write_file(p, json.dumps(data), "utf-8")
        assert read_json(p) == data
