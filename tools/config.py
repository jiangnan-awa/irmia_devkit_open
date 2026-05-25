"""
tools/config.py — 插件级配置共享模块。
main.py 在 __init__ 时调用 set_config 注入配置，各工具模块通过 get_config 读取。
"""
from pathlib import Path

_plugin_dir: Path | None = None
_config: dict = {}


def set_config(config: dict, plugin_dir: str = "") -> None:
    """由 main.py 在插件初始化时调用，注入配置和插件目录路径。"""
    global _config, _plugin_dir
    _config = config or {}
    if plugin_dir:
        _plugin_dir = Path(plugin_dir)


def get_config() -> dict:
    """获取当前配置 dict。各工具模块调用此函数读取配置。"""
    return _config


def get_plugin_dir() -> Path | None:
    """获取插件根目录路径。"""
    return _plugin_dir
