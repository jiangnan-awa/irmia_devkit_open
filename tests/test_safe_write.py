"""Tests for safe_write — new file / overwrite tool."""

from pathlib import Path
from tools.safe_write import write


class TestSafeWrite:
    def test_create_new_file(self, tmp_dir):
        """新建文件应成功"""
        fp = Path(tmp_dir) / "new.txt"
        result = write(str(fp), "hello world")
        assert result["ok"] is True
        assert result["created"] is True
        assert fp.read_text() == "hello world"

    def test_create_nested_dir(self, tmp_dir):
        """父目录不存在时自动创建"""
        fp = Path(tmp_dir) / "a" / "b" / "c.txt"
        result = write(str(fp), "nested")
        assert result["ok"] is True
        assert result["created"] is True
        assert fp.read_text() == "nested"

    def test_existing_no_overwrite(self, tmp_dir):
        """已存在文件且 overwrite=False 应返回 proposal"""
        fp = Path(tmp_dir) / "exist.txt"
        fp.write_text("original")
        result = write(str(fp), "new content")
        assert result["ok"] is False
        assert "文件已存在" in result.get("error", "")
        assert fp.read_text() == "original"  # 未修改

    def test_existing_overwrite(self, tmp_dir):
        """overwrite=True 应覆盖并保留备份"""
        fp = Path(tmp_dir) / "overwrite.txt"
        fp.write_text("original content")
        result = write(str(fp), "new content", overwrite=True)
        assert result["ok"] is True
        assert result["overwritten"] is True
        assert fp.read_text() == "new content"
        assert "backup" in result  # 应有备份

    def test_path_traversal_blocked(self, tmp_dir):
        """路径穿越应被拒绝"""
        result = write(str(Path(tmp_dir) / ".." / "escape.txt"), "test")
        assert result["ok"] is False
        assert "穿越" in result.get("error", "")

    def test_none_content(self, tmp_dir):
        """content=None 应报错"""
        result = write(str(Path(tmp_dir) / "none.txt"), None)
        assert result["ok"] is False
