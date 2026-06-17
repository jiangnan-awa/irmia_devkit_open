"""Tests for es_search — Linux fallback 路径与参数传递。"""

import os
from pathlib import Path
from unittest import mock

from tools import config as _tool_config
from tools.es_search import (
    _apply_extra_filters,
    _apply_sort,
    _python_fallback_search,
    search,
)


class TestPythonFallback:
    def test_basic_substring_match(self, tmp_dir):
        """默认字面子串匹配应能找到文件。"""
        (Path(tmp_dir) / "alpha.py").write_text("x = 1\n")
        (Path(tmp_dir) / "beta.txt").write_text("y = 2\n")
        r = _python_fallback_search("alpha", tmp_dir, 100, False, "file", "")
        assert r["ok"] is True
        assert r["engine"] == "python"
        names = [it["name"] for it in r["items"]]
        assert "alpha.py" in names
        assert "beta.txt" not in names

    def test_regex_match(self, tmp_dir):
        """regex=True 应使用正则匹配。"""
        (Path(tmp_dir) / "test_001.py").write_text("")
        (Path(tmp_dir) / "test_002.py").write_text("")
        (Path(tmp_dir) / "other.py").write_text("")
        r = _python_fallback_search(r"test_\d+", tmp_dir, 100, False, "file", "", regex=True)
        names = sorted(it["name"] for it in r["items"])
        assert names == ["test_001.py", "test_002.py"]

    def test_invalid_regex_returns_error(self, tmp_dir):
        r = _python_fallback_search("(unclosed", tmp_dir, 100, False, "file", "", regex=True)
        assert r["ok"] is False
        assert "正则" in r["error"]

    def test_whole_word(self, tmp_dir):
        """whole_word=True 只匹配完整单词，不匹配子串。"""
        (Path(tmp_dir) / "run.py").write_text("")
        (Path(tmp_dir) / "running.py").write_text("")
        r = _python_fallback_search("run", tmp_dir, 100, False, "file", "", whole_word=True)
        names = sorted(it["name"] for it in r["items"])
        assert names == ["run.py"]

    def test_ext_filter(self, tmp_dir):
        (Path(tmp_dir) / "a.py").write_text("")
        (Path(tmp_dir) / "a.txt").write_text("")
        r = _python_fallback_search("a", tmp_dir, 100, False, "file", "py")
        assert all(it["name"].endswith(".py") for it in r["items"])

    def test_sort_by_size(self, tmp_dir):
        (Path(tmp_dir) / "small.py").write_text("a")
        (Path(tmp_dir) / "big.py").write_text("a" * 1000)
        r = _python_fallback_search("py", tmp_dir, 100, False, "file", "py", sort_by="size")
        sizes = [it["size"] for it in r["items"]]
        assert sizes == sorted(sizes, reverse=True)

    def test_hint_is_cross_platform(self, tmp_dir):
        r = _python_fallback_search("nonexistent_xyz", tmp_dir, 100, False, "file", "")
        note = r["note"]
        # 同时包含 Linux 与 Windows 提示
        assert ("fd" in note or "locate" in note)
        assert ("brew" in note or "apt" in note or "dnf" in note)


class TestApplyHelpers:
    def test_apply_sort_size(self):
        items = [{"name": "a", "size": 10}, {"name": "b", "size": 100}, {"name": "c", "size": 1}]
        out = _apply_sort(items, "size", 10)
        assert [it["size"] for it in out] == [100, 10, 1]

    def test_apply_sort_invalid_key_passthrough(self):
        items = [{"name": "a"}, {"name": "b"}]
        out = _apply_sort(items, "date_created", 10)
        assert out == items

    def test_apply_extra_filters_whole_word(self):
        items = [{"name": "run.py"}, {"name": "running.py"}, {"name": "prerun.py"}]
        out = _apply_extra_filters(items, "run", regex=False, whole_word=True, case_sensitive=False)
        assert [it["name"] for it in out] == ["run.py"]

    def test_apply_extra_filters_regex(self):
        items = [{"name": "a1.py"}, {"name": "a2.py"}, {"name": "b.py"}]
        out = _apply_extra_filters(items, r"a\d", regex=True, whole_word=False, case_sensitive=False)
        assert sorted(it["name"] for it in out) == ["a1.py", "a2.py"]

    def test_apply_extra_filters_noop(self):
        items = [{"name": "a"}, {"name": "b"}]
        out = _apply_extra_filters(items, "a", regex=False, whole_word=False, case_sensitive=False)
        assert out == items


class TestSearchDispatch:
    def test_dispatch_to_posix_when_es_missing(self, tmp_dir):
        """es_path 解析到不存在的路径时，应进入 posix fallback 并尊重 regex 参数。"""
        (Path(tmp_dir) / "test_42.py").write_text("")
        _tool_config.set_config({"es_path": ""}, plugin_dir="")
        with mock.patch("tools.es_search._get_es_path", return_value="es"), \
             mock.patch("tools.es_search.shutil.which", return_value=None):
            # "es" 这个相对路径通常不存在 → 走 fallback
            r = search(r"test_\d+", path=tmp_dir, file_type="file", regex=True)
        assert r["ok"] is True
        names = [it["name"] for it in r["items"]]
        assert "test_42.py" in names
