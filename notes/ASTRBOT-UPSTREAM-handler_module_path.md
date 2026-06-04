# AstrBot 上游问题报告：handler_module_path 路径不匹配导致工具状态损坏

**发现日期**: 2026-06-04  
**影响版本**: AstrBot v4.25.x  
**严重度**: Medium（单次工具状态丢失，可手动恢复）  
**报告方**: 弥亚开发工具箱 (irmia_devkit_open v2.3.6)

---

## 一句话总结

`StarContext.add_llm_tools` 和 `star_manager` 对 `handler_module_path` 使用不同路径体系，导致插件禁用/启用时 `startswith` 匹配失败，工具状态被破坏。

---

## 责任判定

AstrBot 上游问题。插件开发文档未提及 `handler_module_path`，开发者只调用文档推荐的 `context.add_llm_tools()`，无法预知内部需要对齐 `data.plugins.` 前缀。任何把工具类放在子模块（如 `tools/` 目录）的插件都会触发。

---

## 根因

`StarContext.add_llm_tools` 构建 `handler_module_path` 时使用纯模块路径：

```
astrbot_plugin_irmia_devkit.tools.safe_edit
```

`star_manager` 的 deactivate/activate 用完整路径做匹配：

```python
# star_manager.py:1703
plugin.module_path.startswith(mp)  # mp = func_tool.handler_module_path
```

而 `plugin.module_path` = `data.plugins.astrbot_plugin_irmia_devkit.main`

```
"data.plugins.astrbot_plugin_irmia_devkit.main"
    .startswith("astrbot_plugin_irmia_devkit.tools.safe_edit")
→ FALSE
```

导致 deactivate/activate 时所有工具被跳过，`inactivated_llm_tools` 持久化列表出现幽灵条目。

此外，条件 `plugin.module_path.startswith(mp)` 的语义是反的——应该是 `mp.startswith(plugin.module_path)`。前者要求插件模块路径是工具模块路径的**前缀**（几乎永远不成立），后者检查工具是否**属于**该插件（合理语义）。

---

## 复现步骤

1. 在插件自身配置中禁用一组工具 → WebUI 函数工具管理里该组消失
2. 停用插件 → 剩余工具被标为停用
3. 在插件配置中重新启用那组工具
4. WebUI 函数工具管理 → 该插件所有工具全部消失
5. 启用插件
6. 工具重新出现，但全部为关闭状态

---

## 影响范围

**所有把工具类放在子目录（如 `tools/` 或 `utils/`）的插件**

- 触发条件：插件 reload、AstrBot 重启/更新时内部 deactivate→activate 循环
- 用户感知：未曾手动禁用的工具在 WebUI 显示为关闭

---

## 插件侧 workaround

```python
# main.py 工具注册后
_PLUGIN_MODULE_PREFIX = "data.plugins.astrbot_plugin_irmia_devkit"
for tool in tools:
    tool.handler_module_path = _PLUGIN_MODULE_PREFIX
```

---

## 建议上游修复

1. `StarContext.add_llm_tools`（`star/context.py:494`）在构建 `handler_module_path` 时加 `data.plugins.` 前缀，或改用模块的完整 import 路径
2. `star_manager.py:1703` 的 `plugin.module_path.startswith(mp)` 改为 `mp.startswith(plugin.module_path)`
3. 至少文档说明 `handler_module_path` 的约束
