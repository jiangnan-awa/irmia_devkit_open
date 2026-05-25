# 弥亚开发工具箱 (Irmia DevKit)

AstrBot 插件 — 为 LLM Agent 提供安全、精确的代码开发工具集。

**要求**: Python ≥ 3.10, AstrBot 任意版本。

## 工具组

54 个工具按 9 组管理，可在 `config.json` 中按组开关（`false` = 整组禁用），也可通过 `disabled_tools` 单独关闭特定工具。WebUI 面板同样支持。**修改后需重启 AstrBot 生效**。



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

## 前置依赖

| 工具 | 依赖 | 未安装时的行为 |
|------|------|---------------|
| `es_search` | [Everything](https://www.voidtools.com/) + es.exe | 返回错误提示 |
| `gh_cli` | [GitHub CLI](https://cli.github.com/) | 返回错误提示 |
| `html_extract` | `pip install beautifulsoup4 lxml` | 导入失败时报错 |
| `syntax_check` (Nim) | Nim 编译器 | 跳过语法检查 (skipped=true) |
| `syntax_check` (Go) | Go 编译器 | 跳过语法检查 |
| `syntax_check` (JS/TS) | Node.js | 跳过语法检查 |
| `proc_list` / `sys_snapshot` | Windows (tasklist / systeminfo) | 返回错误提示 |

> 其余 30+ 个工具为纯 Python 标准库，零外部依赖。

## 工具列表 (54 个)

### 🔒 安全编辑链

| 工具 | 用途 |
|------|------|
| `safe_edit` | 自动备份→精确替换→语法检查→通过保留/失败自动回滚。**改代码的唯一入口** |
| `safe_rollback` | 回滚文件到指定备份或最近备份 |
| `safe_backups` | 列出所有备份文件 |
| `file_patch` | 精确替换文本，用于非代码文件 |
| `file_preview` | 预览替换效果 (dry-run diff) |
| `syntax_check` | Python / Nim / Go / JS / TS 语法检查 |

### 🔀 Git 操作

| 工具 | 用途 |
|------|------|
| `git_status` | 仓库状态 (--porcelain 结构化输出) |
| `git_diff` | 工作区/暂存区差异 |
| `git_log` | 最近 N 条提交记录 |
| `git_commit` | 暂存全部 + 提交（>10 文件拦截） |
| `git_branch` | 当前分支名 |
| `git_remote` | 远程仓库 URL |
| `git_push` | 推送到 origin（无 --force） |

### 🐙 GitHub CLI

| 工具 | 用途 |
|------|------|
| `gh_cli` | PR / Issue / Release / CI / 仓库 — 13 种操作 |

### 🔍 文件系统与搜索

| 工具 | 用途 |
|------|------|
| `es_search` | Everything 毫秒级文件名搜索 |
| `dir_tree` | 目录树可视化 |
| `dir_list` | 目录列表（结构化） |
| `file_diff` | 两文件差异比较 |
| `file_hash` | MD5 / SHA1 / SHA256 计算 |
| `file_zip` | ZIP 打包 |
| `file_unzip` | ZIP 解压（含 Zip-slip 防护） |
| `disk_info` | 所有磁盘分区使用情况（Windows/Linux） |
| `file_watch` | 目录文件变化监控 |
| `config_diff` | JSON/YAML 配置文件 key 级差异比较 |

### 💻 系统信息

| 工具 | 用途 |
|------|------|
| `port_check` | 端口检测 / 批量扫描 |
| `proc_list` | 进程列表（Windows/Linux） |
| `sys_snapshot` | 系统快照（CPU/内存/进程数/开机时间） |

### 🌐 网络

| 工具 | 用途 |
|------|------|
| `http_get` | HTTP GET（SSRF 防护） |
| `http_post` | HTTP POST（自动 JSON 编码） |
| `http_download` | 二进制下载（500MB 上限 + 路径沙箱） |

### 📝 文本处理

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

### 🔧 实用工具

| 工具 | 用途 |
|------|------|
| `base64_encode` / `_decode` | Base64 编解码 |
| `url_encode` / `_decode` | URL 编解码 |
| `hex_encode` / `_decode` | 十六进制编解码 |
| `time_now` | 当前时间（ISO + 时间戳） |
| `ts_to_iso` | 时间戳→ISO 字符串 |
| `iso_to_ts` | ISO 字符串→时间戳 |
| `time_diff` | 两个 ISO 时间的差值 |
| `semver_compare` | 语义版本号比较 |
| `uuid_gen` | UUID4 / hex / token 生成（密码学安全） |
| `svg_render` | SVG→PNG 渲染（可选 cairosvg） |
| `json_schema_val` | JSON Schema 校验（可选 jsonschema） |

### 🧠 Skill

| 名称 | 触发条件 | 行为 |
|------|----------|------|
| `dev-workflow` | 收到编码/改代码/修bug/重构任务 | 强制走安全编辑 + 语法检查 + git 自检流程 |

## 版本

**1.5.0** — 跨平台支持 + 工具拆分 + 新工具 + 工具组开关

## 作者

伊尔弥亚 (irmia2026)

https://github.com/irmia2026/irmia_devkit_open
