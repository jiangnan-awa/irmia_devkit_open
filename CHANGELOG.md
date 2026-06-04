# Changelog

## v2.3.7 — 工具管理权收回 + 四层防御上线

- **工具管理权收回**: 不再覆写 `handler_module_path` 强制对齐 AstrBot，改为利用 `startswith` 方向差异：`_PLUGIN_MODULE_PREFIX` 不带 `.main` 后缀，使 `turn_off_plugin` 能正确停用、`_unbind_plugin` 不被误删
- **四层防御**: `__init__` 自愈（`_heal_inactivated_tools`）→ `on_plugin_loaded` 钩子纠正 L1091 覆写（`_post_load_heal`）→ 请求级兜底（`_auth_guard` 自愈）→ `star_map` alias 修复 WebUI 来源显示
- **上游问题**: 定位并报告 4 个 AstrBot 上游 bug（`config.py` 停用时无差别 reload、`startswith` 方向反 ×2、`turn_on_plugin` 重启路径缺失、`handler_module_path` 前缀不一致）
- **防御**: `_auth_guard` 取消 L2 原生工具摘除实验（已回退），回到纯 L1 模式，管理员路径零开销；日志降级避免刷屏
- **DB 自愈**: 直接清理 SQLite 中 `inactivated_llm_tools` 的幽灵条目

## v2.3.6 — 群级 WebUI + handler_module_path 修正

- **群级权限配置 (PR #4)**: 新增 `devkit_web.py` Web 管理面板 — 按群聊独立配置工具箱权限（额外管理员、工具组开关），支持全局管理员和群级额外管理员双层鉴权
- **配置**: 新增 `group_config_enabled` 开关（默认关闭），`config.json` / `_conf_schema.json` 同步
- **前端**: `pages/settings/` — 蓝白主题 WebUI，群列表侧边栏 + 配置面板，XSS 防护，确认弹窗，Toast 提示
- **AstrBot 兼容修复**: `handler_module_path` 从子模块路径（`astrbot_plugin_irmia_devkit.tools.xxx`）改为插件根路径（`data.plugins.astrbot_plugin_irmia_devkit`），对齐 `star_manager` 的 deactivate/activate 路径匹配逻辑，修复插件禁用/启用后工具被意外关闭的问题
- **上游问题**: 发现并报告 AstrBot `star_manager.py` 中 `plugin.module_path.startswith(mp)` 的比较方向反了（应 `mp.startswith(plugin.module_path)`），导致插件禁用/启用时工具状态持久化损坏；含完整 6 步复现路径和插件侧 workaround
- **日志优化**: L2 摘除实验（已回退）；`_auth_guard` 回到纯 L1 模式，管理员路径零开销

## v2.3.5 — 双层权限防线 + 代码审查修复

- **权限防线 (P0)**: 新增 `tools/_auth.py` 模块 — `protect_tool()` 包裹每个工具的 `call()` 执行前鉴权；`build_allowed_ids()` 自动读取 AstrBot 全局管理员列表 + 插件额外配置
- **钩子清理 (P0)**: `main.py` 新增 `_auth_guard` — `on_llm_request` 钩子按 `handler_module_path` 清空本插件工具，非管理员 LLM 不可见
- **配置**: `config.json` / `_conf_schema.json` 新增 `owner_sid`、`allowed_ids` 字段
- **测试**: 新增 `test_auth.py` — 20 用例覆盖 `protect_tool` 放行/拦截/异常、`build_allowed_ids` 合并/降级、Layer 1 过滤逻辑（共 120 用例）
- **代码审查修复**: 三轮审查修复 18 项问题 — `_allowed_ids` 缓存同步、`_rebuild_func_tool` 静默失败→告警、`http_download` 反模式消除、`syntax_check` 异常限窄+TimeoutExpired、`rg_search` whole_word `re.escape`、死 import 清理、`flag_map` 提取常量等
- **交叉验证修复**: 第五轮全量审查 + AstrBot 源码交叉比对，修复 25 项 — `safe_edit` 回滚+备份异常捕获、`regex_tester` `replace()` 超时保护、`gh_cli` 临时文件泄漏、`es_search` regex+ext 冲突、`file_zip` 符号链接 SymlinkGuard、`rg_search` 错误区分、`_auth` 多配置管理员同步、`port_check` socket 初始化、`csv_utils` 行上限、`semver` v 前缀、`log_parse` 精确匹配等
- **API 规范化**: `_registry.py` 移除无效 `func_type` 字段；`_auth.py`/`main.py` 改用 `event.is_admin()` 替代 `getattr`
- **缺陷**: 零存量已知缺陷

## v2.3.0 — 基础层补完 (60→61)

- **新工具**: `rg_search` — 文件内容级代码搜索引擎（ripgrep + Python fallback），支持正则、全词匹配、文件类型过滤、上下文展示
- **编辑增强 (P0)**: `safe_edit`/`file_patch` 加 whitespace-tolerant 匹配（对标 Aider），精确匹配失败时自动对齐行首空白重试
- **上下文赋能 (P0)**: `rg_search` 支持 `context_lines` 参数（rg -C），`lint_runner` 返回错误行前后代码片段，`syntax_check` 语法错误附带上下文标记
- **Git 增强 (P0)**: `git_diff` 返回结构化统计（files_changed/added/removed/total_changes）
- **linter fallback**: `lint_runner` 的 ruff↔pylint 互 fallback——首选未安装时自动切换备用 linter
- **架构重构 (P1)**: 提取 `_run_cmd()` 统一 subprocess 封装，7 个文件收口；`http_get`/`http_download` 共享 `make_opener`/`check_url`；`config_diff`/`project_init`/`dep_scan` 统一 encoding fallback
- **psutil 条件引入 (P1)**: `proc_list` 优先使用 psutil（跨平台 + 性能优化），不可用时 fallback 原有实现
- **防御加固 (P2)**: `json_query` 加递归深度限制 (50)、`dir_tree`/`dir_list` 共享 `SymlinkGuard`、`safe_edit` 备份前预检磁盘空间、`db_query` SQLite URI 跨平台路径修复
- **测试**: 从 51 用例扩展到 100 用例（+rg_search、+lint_runner fallback、+file_remove 沙箱、+syntax_check context、+registry 一致性检查、+helpers unwrap 透传）
- **文档**: 新增 `ARCHITECTURE.md`（模块图/数据流/新增工具指南/安全架构）、`README_EN.md`
- **修复**: `file_patch` 缺 `difflib` import → NameError、`_registry` `TimeDiffTool` 重复定义、`_parse_rg_output` 冒号解析跨平台 bug、`main.py` config 路径改用 `StarTools.get_data_dir()`
- **依赖**: 新增 `rg_search` 可选依赖 ripgrep（未安装时 Python fallback）

## v2.2.0 — 统一交互协议

- **proposal 协议**: 新增 `proposal_reply()` 工厂函数，17 个工具的失败/歧义返回统一为 `{proposal, evidence, options, next_call}` 四字段结构化提案。覆盖 `safe_edit`、`git_commit`、`syntax_check`、`port_check`、`es_search`、`lint_runner`、`dep_scan`、`config_diff`、`log_parse`、`text_filter` 等
- **测试**: 新建 `tests/` 目录，51 个 pytest 用例覆盖 SSRF、safe_edit 安全链、Zip-slip、SQL 注入、正则回溯、helpers 协议、git commit 守卫
- **AstrBot 合规**: `requirements.txt`、`astrbot_version`、`short_desc`、`support_platforms`、`logo.png`
- **ruff**: 全项目格式化 + `pyproject.toml` 配置
- **修复**: `_http_utils` 域名路径 NameError、`sys_snapshot` `_extract_mb` 缺失、`_conf_schema.json` trailing comma、`safe_edit` 接入 `backup_dir` 配置、HTTP redirect SSRF 重新校验、gh_cli try/finally 临时文件清理、`human_size` TB/PB 兜底、备份文件名微秒防撞

## v2.0.0 — 生态扩展 (60→63)

- **新工具**: `tool_stats` 调用统计、`db_query` SQLite 只读查询（参数化防注入）、`dep_scan` Python import 依赖图 + 循环引用检测
- **优雅打磨**: tool_stats 注入率 100%、`_registry.py` 9 组分区注释、README 快速索引

## v1.8 — 质量层 (59→60)

- **新工具**: `lint_runner` — ruff/pylint/eslint 代码质量检查，与 `syntax_check` 互补

## v1.7 — 决策层 (57→59)

- **新工具**: `project_init` 项目结构扫描（detect 语言/框架/依赖）、`git_changelog` git log 语义分组

## v1.6 — 架构收口 + 安全加固 (54→57)

- **架构**: GhCliTool 拆为 `gh_pr`/`gh_issue`/`gh_release`/`gh_repo` 4 独立工具；注册表外移至 `tools/_registry.py`，main.py 1580→113 行
- **安全**: IPv4-mapped-IPv6 SSRF 检查、正则嵌套量词拒绝（防 ReDoS）
- **质量**: file_watch 每轮 rglob 重扫、UA 统一、bare except 加错误信息

## v1.5 — 新工具 (49→54)

- **新工具**: `log_parse` 日志解析、`file_watch` 文件监控、`config_diff` 配置文件 key 级对比、`svg_render` SVG→PNG、`json_schema_val` JSON Schema 校验
- **增强**: `text_filter` 新增 `regex=True` 正则模式

## v1.4 — 质量打磨 (41→49)

- **工具拆分**: `encode_utils` 拆为 6 独立工具（base64/url/hex encode/decode）；`time_utils` 拆为 4 独立工具（now/ts_to_iso/iso_to_ts/time_diff）
- **提取**: `_helpers.py` 共享辅助模块
- **修复**: `syntax_check` Python GBK fallback

## v1.3 — 跨平台 (41)

- **Linux 回退**: `proc_list` ps aux、`disk_info` POSIX、`sys_snapshot` /proc
- **降级**: `html_extract` lxml→html.parser fallback

## v1.2.1 — Bugfix (41)

- **修复**: `file_patch` 编码保留（GBK 读→UTF-8 写回）、清理 `_ok` 死代码
- **文档**: README Python ≥3.10、.gitignore 补全

## v1.2.0 — 初始发布 (42→41)

- **配置系统**: `config.json` + `_conf_schema.json` + `tools/config.py`
- **路径脱敏**: 移除 5 处硬编码路径
- **安全修复**: SSRF DNS 重绑定、es_search 参数索引、json_query [-1] 正则、opencode 环境变量白名单
- **Git**: 7 工具 description 加"替代原生命令"前缀
- **移除**: opencode 工具及所有残留引用
