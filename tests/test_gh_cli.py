"""Tests for gh_cli — 跨平台路径发现与安装提示。"""

import platform
from unittest import mock

from tools import config as _tool_config
from tools.gh_cli import _find_gh, _install_hint, _is_windows


class TestFindGh:
    def test_custom_path_wins(self, tmp_path):
        fake = tmp_path / "gh"
        fake.write_text("")
        _tool_config.set_config({"gh_path": str(fake)}, plugin_dir="")
        assert _find_gh() == str(fake)

    def test_missing_custom_falls_through(self):
        _tool_config.set_config({"gh_path": "/nonexistent/gh"}, plugin_dir="")
        # 自定义路径不存在 → 走 which / guesses；断言不返回那个不存在的路径
        result = _find_gh()
        assert result != "/nonexistent/gh"

    def test_which_called(self):
        """shutil.which 命中时直接返回（不依赖具体安装）。"""
        _tool_config.set_config({}, plugin_dir="")
        with mock.patch("tools.gh_cli.shutil.which", return_value="/usr/bin/gh"):
            assert _find_gh() == "/usr/bin/gh"

    def test_linux_guesses_returned_when_found(self):
        """非 Windows 下若 guesses 命中已存在的文件，应返回该路径。"""
        if _is_windows():
            return  # 跳过 Windows 环境
        _tool_config.set_config({}, plugin_dir="")
        with mock.patch("tools.gh_cli.shutil.which", return_value=None), \
             mock.patch("tools.gh_cli.platform.system", return_value="Linux"), \
             mock.patch("os.path.exists", side_effect=lambda p: p == "/usr/local/bin/gh"):
            assert _find_gh() == "/usr/local/bin/gh"

    def test_fallback_to_gh_when_nothing_found(self):
        _tool_config.set_config({}, plugin_dir="")
        with mock.patch("tools.gh_cli.shutil.which", return_value=None), \
             mock.patch("os.path.exists", return_value=False):
            assert _find_gh() == "gh"


class TestInstallHint:
    def test_windows_hint(self):
        with mock.patch("tools.gh_cli.platform.system", return_value="Windows"):
            assert "winget" in _install_hint()

    def test_linux_hint(self):
        with mock.patch("tools.gh_cli.platform.system", return_value="Linux"):
            hint = _install_hint()
            assert "apt" in hint or "brew" in hint or "dnf" in hint

    def test_macos_hint(self):
        with mock.patch("tools.gh_cli.platform.system", return_value="Darwin"):
            assert "brew" in _install_hint()
