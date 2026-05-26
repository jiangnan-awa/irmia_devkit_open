# 弥亚开发工具箱 (Irmia DevKit)

AstrBot 插件 — 为 LLM Agent 提供安全、精确的代码开发工具集。

**要求**: Python ≥ 3.10, AstrBot 任意版本。

> ⚠️ 本插件为本地单人开发辅助工具。不建议在公网多用户共享 Bot 场景下部署。所有文件操作工具仅限工作目录内。

## 安装

将插件文件夹放入 AstrBot 的 `data/plugins/` 目录，重启 AstrBot 即可。

```
data/plugins/
└── astrbot_plugin_irmia_devkit/
    ├── main.py
    ├── metadata.yaml
    ├── config.json
    ├── _conf_schema.json
    ├── tools/
    │   ├── safe_edit.py
    │   ├── git_smart.py
    │   ├── ...
    │   └── config.py
    └── skills/
        └── dev-workflow/
            └── SKILL.md
```

## 配置

首次启动时自动生成 `config.json`。所有字段留空即自动检测。也可通过 AstrBot WebUI 面板配置。

| 字段 | 说明 | 默认 |
|------|------|------|
| `es_path` | Everything CLI 路径 | 空 → `shutil.which("es")` → `"es"` |
| `gh_path` | GitHub CLI 路径 | 空 → `shutil.which("gh")` → `"gh"` |
| `state_dir` | 异步任务状态目录 | 空 → `<插件目录>/state/tasks` |
| `lock_dirs` | 文件锁检测目录列表 | `[]` |
| `backup_dir` | safe_edit 备份目录 | 空 → `~/.irmia/backups` |

## 工具组

63 个工具按 9 组管理。在 `config.json` 中设 `tool_groups` 的组为 `false` 关闭整组，或用 `disabled_tools` 逗号分隔禁用单个工具。WebUI 面板同样支持。**修改后需重启 AstrBot**。

| 字段 | 说明 |
|------|------|
| `tool_groups` | 9 组 bool 开关（`false` = 关闭整组） |
| `disabled_tools` | 单独禁用的工具名（逗号分隔，如 `git_push,svg_render`） |

## 前置依赖

| 工具 | 依赖 | 未安装时的行为 |
|------|------|---------------|
| `es_search` | [Everything](https://www.voidtools.com/) + es.exe | 返回错误提示 |
| `gh_pr` / `gh_issue` / `gh_release` / `gh_repo` | [GitHub CLI](https://cli.github.com/) | 返回错误提示 |
| `html_extract` | `pip install beautifulsoup4`（lxml 可选） | bs4 必装，lxml 缺失回退 html.parser |
| `syntax_check` (Nim) | Nim 编译器 | 跳过 (skipped=true) |
| `syntax_check` (Go) | Go 编译器 | 跳过 |
| `syntax_check` (JS/TS) | Node.js | 跳过 |
| `lint_runner` | `pip install ruff` 或 `pylint` 或 `npm install -g eslint` | 返回安装提示 |
| `json_schema_val` | `pip install jsonschema`（可选） | 返回安装提示 |
| `config_diff` (YAML) | `pip install pyyaml`（可选） | 返回安装提示 |

> 其余 40+ 个工具为纯 Python 标准库，零外部依赖。

## 协议

失败/歧义返回统一为四字段提案，帮助 LLM 快速定位和选择下一步：
- `proposal` — 自然语言：发生了什么、可以做什么
- `evidence` — 结构化证据（支持提案的数据）
- `options` — 离散选项列表
- `next_call` — 预格式化的下次调用参数

覆盖工具：`safe_edit`、`git_commit`、`syntax_check`、`port_check`、`es_search`、`lint_runner`、`dep_scan`、`config_diff`、`log_parse`、`text_filter` 等 17 个工具。`ok:true` 的正常路径不受影响。

## 工具列表 (63 个)

> 快速查找: `safe_edit` / `git_commit` / `es_search` / `http_get` / `log_parse` / `base64_encode` / `time_now` / `project_init` / `lint_runner` / `db_query` ...

### 🔒 安全编辑链 (7)

| 工具 | 用途 |
|------|------|
| `safe_edit` | 自动备份→精确替换→语法检查→通过保留/失败自动回滚。**改代码的唯一入口** |
| `safe_rollback` | 回滚文件到指定备份或最近备份 |
| `safe_backups` | 列出所有备份文件 |
| `file_patch` | 精确替换文本，用于非代码文件 |
| `file_preview` | 预览替换效果 (dry-run diff) |
| `syntax_check` | Python / Nim / Go / JS / TS 语法检查（能不能跑） |
| `lint_runner` | ruff/pylint/eslint 代码质量检查（写得好不好） |

### 🔀 Git & GitHub (11)

| 工具 | 用途 |
|------|------|
| `git_status` | 仓库状态 (--porcelain 结构化输出) |
| `git_diff` | 工作区/暂存区差异 |
| `git_log` | 最近 N 条提交记录 |
| `git_commit` | 暂存全部 + 提交（>10 文件拦截） |
| `git_branch` | 当前分支名 |
| `git_remote` | 远程仓库 URL |
| `git_push` | 推送到 origin（无 --force） |
| `gh_pr` | Pull Request：创建/列出/合并/查看 |
| `gh_issue` | Issue：创建/列出/关闭 |
| `gh_release` | Release：创建发布/列出 |
| `gh_repo` | 仓库：创建/查看/CI状态/认证检查 |

### 📁 文件系统 (10)

| 工具 | 用途 |
|------|------|
| `es_search` | Everything 毫秒级文件名搜索 |
| `dir_tree` | 目录树可视化 |
| `dir_list` | 目录列表（结构化） |
| `file_diff` | 两文件差异比较 |
| `file_hash` | MD5 / SHA1 / SHA256 计算 |
| `file_zip` | ZIP 打包 |
| `file_unzip` | ZIP 解压（含 Zip-slip 防护） |
| `disk_info` | 磁盘分区使用情况（Windows/Linux） |
| `file_watch` | 目录文件变化监控 |
| `config_diff` | JSON/YAML 配置文件 key 级差异比较 |

### 📊 系统信息 (4)

| 工具 | 用途 |
|------|------|
| `port_check` | 端口检测 / 批量扫描 |
| `proc_list` | 进程列表（Windows/Linux） |
| `sys_snapshot` | 系统快照（CPU/内存/进程数/开机时间） |
| `tool_stats` | 工具调用统计（次数/总数） |

### 🌐 网络 (3)

| 工具 | 用途 |
|------|------|
| `http_get` | HTTP GET（SSRF 防护） |
| `http_post` | HTTP POST（自动 JSON 编码） |
| `http_download` | 二进制下载（500MB 上限 + 路径沙箱） |

### 📝 文本处理 (10)

| 工具 | 用途 |
|------|------|
| `html_extract` | HTML → 纯文本 / 链接 / 表格 / CSS 选择器 |
| `json_query` | jq 式 JSON 路径查询 |
| `text_filter` | 行过滤（grep / head / tail / count / invert） |
| `diff_strings` | 字符串 unified diff |
| `regex_test` | 正则匹配测试 |
| `regex_replace` | 正则替换（支持 `\1` 反向引用） |
| `csv_parse` | CSV / TSV → 结构化数据 |
| `csv_gen` | 结构化数据 → CSV / TSV |
| `md_strip` | Markdown → 纯文本 |
| `log_parse` | Nginx/Apache/syslog/JSON Lines 日志解析 |

### 🔤 编码 (6)

| 工具 | 用途 |
|------|------|
| `base64_encode` / `_decode` | Base64 编解码 |
| `url_encode` / `_decode` | URL 编解码 |
| `hex_encode` / `_decode` | 十六进制编解码 |

### ⏱ 时间 (4)

| 工具 | 用途 |
|------|------|
| `time_now` | 当前时间（ISO + 时间戳） |
| `ts_to_iso` | 时间戳→ISO 字符串 |
| `iso_to_ts` | ISO 字符串→时间戳 |
| `time_diff` | 两个 ISO 时间的差值 |

### 🧩 扩展 (8)

| 工具 | 用途 |
|------|------|
| `semver_compare` | 语义版本号比较 |
| `uuid_gen` | UUID4 / hex / token 生成（密码学安全） |
| `svg_render` | SVG→PNG 渲染（可选 cairosvg） |
| `json_schema_val` | JSON Schema 校验（可选 jsonschema） |
| `project_init` | 扫描项目：detect 语言/框架/依赖/目录结构 |
| `git_changelog` | git log→分类 changelog（fix/feat/refactor/docs） |
| `db_query` | SQLite 只读查询（参数化防注入） |
| `dep_scan` | Python import 依赖图 + 循环引用检测 |

### 🧠 Skill

| 名称 | 触发条件 | 行为 |
|------|----------|------|
| `dev-workflow` | 收到编码/改代码/修bug/重构任务 | 强制走安全编辑 + 语法检查 + git 自检流程 |

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

当前覆盖：SSRF 防护、safe_edit 安全链、Zip-slip 防护、SQL 注入拦截、正则回溯拒绝、helpers 协议工厂、git commit 守卫。51 用例。

## 版本

**2.2.0** — 统一交互协议 + 测试套件 · [Changelog](CHANGELOG.md)

## 作者

伊尔弥亚 (irmia2026)

https://github.com/irmia2026/irmia_devkit_open
