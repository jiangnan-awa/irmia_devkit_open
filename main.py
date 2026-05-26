"""
astrbot_plugin_irmia_devkit — 弥亚开发工具箱
为弥亚提供安全、精确的代码开发工具：safe_edit、git_smart、syntax_check、file_patch。
"""

from __future__ import annotations

import json
import os
import copy

from astrbot.api import logger, star
from astrbot.api.star import StarTools

from .tools import config as _tool_config

from .tools._registry import TOOL_GROUPS, _ALL_TOOLS

_DEFAULT_CONFIG = {
    "tool_groups": {g: True for g in TOOL_GROUPS},
    "disabled_tools": [],
    "es_path": "",
    "gh_path": "",
    "state_dir": "",
    "lock_dirs": [],
    "backup_dir": "",
}


class Main(star.Star):
    """弥亚开发工具箱插件"""

    def __init__(self, context: star.Context, config: dict = None) -> None:
        super().__init__(context)
        self.context = context

        plug_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            data_dir = StarTools.get_data_dir()
            config_path = os.path.join(str(data_dir), "config.json")
        except Exception:
            config_path = os.path.join(plug_dir, "config.json")
        # 向后兼容：若 data_dir 无配置，从插件目录迁移
        legacy_path = os.path.join(plug_dir, "config.json")
        if not os.path.exists(config_path) and os.path.exists(legacy_path):
            config_path = legacy_path
        _config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    _config = json.load(f)
            except Exception:
                logger.warning("配置文件 config.json 读取失败，使用默认值")
        else:
            _config = copy.deepcopy(_DEFAULT_CONFIG)
            try:
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(_config, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        # AstrBot WebUI 配置优先于 config.json
        if config:
            changed = False
            # paths 嵌套（工具路径）
            paths = config.get("paths", {})
            for key in ("es_path", "gh_path", "state_dir", "backup_dir"):
                if paths.get(key):
                    _config[key] = paths[key]
                    changed = True
            if paths.get("lock_dirs"):
                raw = paths["lock_dirs"]
                if isinstance(raw, str):
                    _config["lock_dirs"] = [
                        d.strip() for d in raw.split(",") if d.strip()
                    ]
                elif isinstance(raw, list):
                    _config["lock_dirs"] = raw
                changed = True
            # tool_groups / disabled_tools（顶层 key）
            web_groups = config.get("tool_groups", {})
            if web_groups and isinstance(web_groups, dict):
                stored = _config.setdefault("tool_groups", {})
                for g, v in web_groups.items():
                    stored[g] = v
                changed = True
            web_disabled = config.get("disabled_tools", "")
            if web_disabled:
                _config["disabled_tools"] = [
                    t.strip() for t in web_disabled.split(",") if t.strip()
                ]
                changed = True
            if changed:
                try:
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(_config, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        _tool_config.set_config(_config, plug_dir)

        # 过滤已启用的工具并注册
        tool_groups = _config.get("tool_groups", {})
        disabled = _config.get("disabled_tools", [])
        enabled = set()
        for group, tool_names in TOOL_GROUPS.items():
            if tool_groups.get(group, True):
                enabled.update(tool_names)
        for t in disabled:
            enabled.discard(t)

        tools = [_ALL_TOOLS[name]() for name in enabled if name in _ALL_TOOLS]
        context.add_llm_tools(*tools)
        logger.info(f"🔧 弥亚开发工具箱已就绪 — {len(tools)} 个工具注册完毕")
