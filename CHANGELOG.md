# Changelog

## v2.2.0 — 统一交互协议

- **proposal 协议**: 新增 `proposal_reply()` 工厂函数，17 个工具的失败/歧义返回统一为 `{proposal, evidence, options, next_call}` 四字段结构化提案。覆盖 `safe_edit`、`git_commit`、`syntax_check`、`port_check`、`es_search`、`lint_runner`、`dep_scan`、`config_diff`、`log_parse`、`text_filter` 等
- **测试**: 新建 `tests/` 目录，51 个 pytest 用例覆盖 SSRF、safe_edit 安全链、Zip-slip、SQL 注入、正则回溯、helpers 协议、git commit 守卫
- **AstrBot 合规**: `requirements.txt`、`astrbot_version`、`short_desc`、`support_platforms`、`logo.png`
- **ruff**: 全项目格式化 + `ruff.toml` 配置
- **修复**: `_http_utils` 域名路径 NameError、`sys_snapshot` `_extract_mb` 缺失、`_conf_schema.json` trailing comma、`safe_edit` 接入 `backup_dir` 配置、HTTP redirect SSRF 重新校验、gh_cli try/finally 临时文件清理、`human_size` TB/PB 兜底、备份文件名微秒防撞

## v2.0 — 生态扩展 (60→63)

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
