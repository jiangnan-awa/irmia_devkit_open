"""
_registry — @dataclass FunctionTool 类定义注册表。
从 main.py 提取，供 plugin entry 使用。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrbot.api import FunctionTool as _AstrBotFunctionTool
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class FunctionTool(_AstrBotFunctionTool):
    """AstrBot v4.16+ 兼容基类。"""

from ._helpers import err_json as _err, unwrap as _unwrap, run_sync as _run_sync
from . import tool_stats as _tool_stats

# ── 导入工具函数 ──

from .file_patch import patch as _file_patch, preview as _file_preview
from .git_smart import (
    status as _git_status,
    diff as _git_diff,
    log as _git_log,
    commit as _git_commit,
    current_branch as _git_branch,
    remote_url as _git_remote,
    push as _git_push,
)
from .syntax_check import check as _syntax_check
from .safe_edit import (
    edit as _safe_edit,
    list_backups as _list_backups,
    rollback as _rollback,
)
from .es_search import search as _es_search
from .rg_search import search as _rg_search
from .http_get import get as _http_get, post as _http_post
from .http_download import download as _http_download
from .html_extract import extract as _html_extract
from .dir_tree import tree as _dir_tree
from .disk_info import info as _disk_info
from .port_check import check as _port_check, scan as _port_scan
from .file_diff import compare as _file_diff
from .proc_list import list_processes as _proc_list
from .file_hash import compute as _file_hash
from .file_zip import compress as _file_zip, extract as _file_unzip
from .sys_snapshot import snapshot as _sys_snapshot
from .encode_utils import (
    b64_encode,
    b64_decode,
    url_encode,
    url_decode,
    hex_encode,
    hex_decode,
)
from .time_utils import now as _time_now, ts_to_iso, iso_to_ts, time_diff
from .regex_tester import test as _regex_test, replace as _regex_replace
from .dir_list import list_dir as _list_dir
from .json_query import query as _json_query
from .text_filter import filter_lines as _text_filter
from .diff_strings import diff as _diff_strings
from .csv_utils import parse as _csv_parse, generate as _csv_gen
from .uuid_gen import gen as _uuid_gen
from .semver import compare as _semver_compare
from .md_strip import strip as _md_strip
from .gh_cli import (
    pr_create as _gh_pr_create,
    pr_list as _gh_pr_list,
    pr_merge as _gh_pr_merge,
    pr_view as _gh_pr_view,
    issue_create as _gh_issue_create,
    issue_list as _gh_issue_list,
    issue_close as _gh_issue_close,
    release_create as _gh_release_create,
    release_list as _gh_release_list,
    repo_view as _gh_repo_view,
    repo_create as _gh_repo_create,
    run_list as _gh_run_list,
    auth_status as _gh_auth_status,
)
from .log_parse import parse as _log_parse
from .file_watch import watch as _file_watch
from .config_diff import diff as _config_diff
from .svg_render import render as _svg_render
from .json_schema_val import validate as _json_schema_val
from .project_init import scan as _project_init_scan
from .git_changelog import changelog as _git_changelog
from .lint_runner import run as _lint_run
from .tool_stats import snapshot as _tool_stats_snap
from .db_query import query as _db_query
from .dep_scan import scan as _dep_scan
from .file_remove import remove as _file_remove

# ── codegraph ──
from .codegraph import CodeGraph as _CodeGraph


def _code_index(project_dir: str, incremental: bool = False) -> dict:
    from pathlib import Path
    root = Path(project_dir).resolve()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.index(str(root), incremental)


def _code_explore(query: str, project_dir: str = ".") -> dict:
    from pathlib import Path
    root = Path(project_dir).resolve()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.explore(query, str(root))


def _code_diff_impact(filepaths: list, max_depth: int = 3) -> dict:
    from pathlib import Path
    root = Path(".").resolve()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.code_diff_impact(filepaths, max_depth)


def _code_pack(target: str, depth: int = 2, mode: str = "both") -> dict:
    from pathlib import Path
    root = Path(".").resolve()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.code_pack(target, depth, mode)


def _code_status() -> dict:
    from pathlib import Path
    root = Path(".").resolve()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.code_status()
    db_path = str(root / ".codegraph" / "codegraph.db")
    cg = _CodeGraph(db_path)
    return cg.explore(query, str(root))

# ═══════════════════════════════════════════════════════════
# Tool classes
# ═══════════════════════════════════════════════════════════


# ══ 安全编辑链 ══
@dataclass
class SafeEditTool(FunctionTool):
    """安全编辑：自动备份→精确替换→语法检查→通过保留/失败回滚。"""

    name: str = "safe_edit"
    description: str = (
        "【改代码文件唯一选择】安全编辑：自动备份→精确替换→语法检查→"
        "通过保留/失败自动回滚。支持 .py/.nim/.go/.js/.ts（语法检查）+ 其他扩展名（跳过语法检查）。"
        "不要用 file_write 改已有代码（无备份无回滚）。不要用 astrbot_file_edit_tool 改代码（无备份无语法检查）。"
        "非代码文件（.md/.txt/.json）可以用 file_patch 或 safe_edit，两者均可。"
        "当 old 文本在文件中多处匹配时，工具会报错并列出所有位置——用 occurrence=N 指定第几次出现继续。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "old": {
                    "type": "string",
                    "description": "要被替换的旧文本（精确匹配，包括缩进）",
                },
                "new": {"type": "string", "description": "替换后的新文本"},
                "replace_all": {
                    "type": "boolean",
                    "description": "是否替换所有匹配项，默认 false",
                    "default": False,
                },
                "occurrence": {
                    "type": "integer",
                    "description": "替换第 N 次出现（1-based）。当多处匹配时用于消歧",
                    "default": 0,
                },
            },
            "required": ["filepath", "old", "new"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        old: str,
        new: str,
        replace_all: bool = False,
        occurrence: int = 0,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(
                _safe_edit, filepath, old, new, replace_all, occurrence
            )
            return _unwrap(result)
        except Exception as e:
            return _err(f"safe_edit 失败: {e}")


@dataclass
class SafeRollbackTool(FunctionTool):
    """回滚文件到备份。"""

    name: str = "safe_rollback"
    description: str = "回滚文件到之前的备份。不指定 backup_name 则回滚到最近一次备份。safe_edit 失败时已自动回滚，此工具用于手动回滚（如改完后不满意想恢复）。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "要回滚的文件路径"},
                "backup_name": {
                    "type": "string",
                    "description": "指定备份文件名，可选",
                },
            },
            "required": ["filepath"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        backup_name: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_rollback, filepath, backup_name or None)
            return _unwrap(result)
        except Exception as e:
            return _err(f"回滚失败: {e}")


@dataclass
class SafeBackupsTool(FunctionTool):
    """查看备份列表。"""

    name: str = "safe_backups"
    description: str = "列出所有备份文件或指定文件的备份。改代码前可先查看有哪些备份；回滚前可确认备份存在。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "要查询备份的文件路径，不传则列出全部",
                }
            },
            "required": [],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], filepath: str = "", **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_list_backups, filepath or None)
            return _unwrap(result)
        except Exception as e:
            return _err(f"查询备份失败: {e}")


@dataclass
class FilePatchTool(FunctionTool):
    """精确文本替换。"""

    name: str = "file_patch"
    description: str = (
        "【替代 astrbot_file_edit_tool——非代码文件首选】精确替换非代码文件中的文本。"
        "不要用 astrbot_file_edit_tool（它找不到旧文本时只报错，无匹配行提示）。"
        "代码文件请用 safe_edit（自动备份+语法检查+失败回滚）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "old": {
                    "type": "string",
                    "description": "要被替换的旧文本（精确匹配）",
                },
                "new": {"type": "string", "description": "替换后的新文本"},
                "replace_all": {
                    "type": "boolean",
                    "description": "是否替换所有匹配项",
                    "default": False,
                },
            },
            "required": ["filepath", "old", "new"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        old: str,
        new: str,
        replace_all: bool = False,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_patch, filepath, old, new, replace_all)
            return _unwrap(result)
        except Exception as e:
            return _err(f"file_patch 失败: {e}")


@dataclass
class FilePreviewTool(FunctionTool):
    """预览替换效果。"""

    name: str = "file_preview"
    description: str = "【file_patch 伴侣】预览替换效果，不实际修改文件，返回 unified diff。用于不确定替换效果时，确认无误后再用 file_patch 实际修改。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "old": {"type": "string", "description": "要被替换的旧文本"},
                "new": {"type": "string", "description": "替换后的新文本"},
                "replace_all": {
                    "type": "boolean",
                    "description": "是否预览全部替换",
                    "default": False,
                },
            },
            "required": ["filepath", "old", "new"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        old: str,
        new: str,
        replace_all: bool = False,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_preview, filepath, old, new, replace_all)
            return _unwrap(result)
        except Exception as e:
            return _err(f"preview 失败: {e}")


@dataclass
class SyntaxCheckTool(FunctionTool):
    """语法检查。"""

    name: str = "syntax_check"
    description: str = (
        "检查代码文件语法。支持 Python/Nim/Go/JS/TS。"
        "safe_edit 内部会自动调用它，所以通常不需要手动调。"
        "仅在用 file_patch 手动改完代码后，才需要手动调此工具验证。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "要检查的文件路径"}
            },
            "required": ["filepath"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], filepath: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_syntax_check, filepath)
            return _unwrap(result)
        except Exception as e:
            return _err(f"syntax_check 失败: {e}")


# ══ Git & GitHub ══
@dataclass
class GitStatusTool(FunctionTool):
    """Git 状态。"""

    name: str = "git_status"
    description: str = (
        "【替代 git status——首选】结构化仓库状态，直接返回 changed_count + changes 列表。"
        "比原生 git status 少一层 --porcelain 手动解析。改前必调。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"cwd": {"type": "string", "description": "Git 仓库路径"}},
            "required": ["cwd"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], cwd: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_status, cwd)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_status 失败: {e}")


@dataclass
class GitDiffTool(FunctionTool):
    """Git diff。"""

    name: str = "git_diff"
    description: str = "【替代 git diff——首选】结构化差异，直接返回 added/removed/total_changes。比原生 git diff 多一层自动统计。改后 staged=false 看工作区，提交前 staged=true 自查。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "description": "Git 仓库路径"},
                "staged": {
                    "type": "boolean",
                    "description": "是否只看已暂存的更改",
                    "default": False,
                },
                "filepath": {"type": "string", "description": "只看指定文件，可选"},
            },
            "required": ["cwd"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        cwd: str,
        staged: bool = False,
        filepath: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_diff, cwd, staged, filepath or None)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_diff 失败: {e}")


@dataclass
class GitLogTool(FunctionTool):
    """Git log。"""

    name: str = "git_log"
    description: str = "【替代 git log——首选】结构化提交记录，直接返回 commits 列表。比原生 git log 少 --format 拼接。提交前确认历史干净时使用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "description": "Git 仓库路径"},
                "count": {
                    "type": "integer",
                    "description": "最近几条，默认 5",
                    "default": 5,
                },
            },
            "required": ["cwd"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        cwd: str,
        count: int = 5,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_log, cwd, count)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_log 失败: {e}")


@dataclass
class GitCommitTool(FunctionTool):
    """Git commit。"""

    name: str = "git_commit"
    description: str = "【替代 git commit——首选】提交并自动生成结构化反馈（files_staged 列表 + 提案）。比原生 git commit 多一层失败诊断。message 用 fix:/feat:/refactor: 格式。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "description": "Git 仓库路径"},
                "message": {"type": "string", "description": "提交信息（简洁描述）"},
            },
            "required": ["cwd", "message"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        cwd: str,
        message: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_commit, cwd, message)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_commit 失败: {e}")


@dataclass
class GitBranchTool(FunctionTool):
    """Git branch。"""

    name: str = "git_branch"
    description: str = "【替代 git branch——首选】直接返回当前分支名。比原生 git branch 少一次 --show-current 手动提取。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"cwd": {"type": "string", "description": "Git 仓库路径"}},
            "required": ["cwd"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], cwd: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_branch, cwd)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_branch 失败: {e}")


@dataclass
class GitRemoteTool(FunctionTool):
    """Git remote URL。"""

    name: str = "git_remote"
    description: str = "【替代 git remote -v——首选】直接返回远程仓库 URL。比原生 git remote -v 少一行文本解析。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"cwd": {"type": "string", "description": "Git 仓库路径"}},
            "required": ["cwd"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], cwd: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_remote, cwd)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_remote 失败: {e}")


@dataclass
class GitPushTool(FunctionTool):
    """Git push。"""

    name: str = "git_push"
    description: str = "【替代 git push——首选】推送并自动保护当前分支。比原生 git push 多一层 --force 防误触。自动获取当前分支名。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "description": "Git 仓库路径"},
                "remote": {"type": "string", "description": "远程名称，默认 origin"},
                "branch": {
                    "type": "string",
                    "description": "分支名，留空自动获取当前分支",
                },
            },
            "required": ["cwd"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        cwd: str,
        remote: str = "origin",
        branch: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_git_push, cwd, remote, branch)
            return _unwrap(result)
        except Exception as e:
            return _err(f"git_push 失败: {e}")


# ══ 文件系统 ══
@dataclass
class EsSearchTool(FunctionTool):
    """Everything 文件名极速搜索。"""

    name: str = "es_search"
    description: str = (
        "【优于 dir /s——首选】毫秒级文件名搜索，直接返回结构化列表（name/path/size/date）。"
        "比 shell dir /s 快 500 倍，比 Python os.walk 简洁 10 倍。"
        "支持通配符（*.py）和 Everything 语法（ext:/folder:/size:）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词。支持通配符如 *.py，以及 ext: folder: size:>1mb 等语法",
                },
                "path": {
                    "type": "string",
                    "description": "限定搜索目录路径。不传则全盘搜索",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数，默认 100。设 0 仅统计数量不返回列表",
                    "default": 100,
                },
                "regex": {
                    "type": "boolean",
                    "description": "使用正则表达式搜索",
                    "default": False,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "区分大小写",
                    "default": False,
                },
                "whole_word": {
                    "type": "boolean",
                    "description": "全词匹配",
                    "default": False,
                },
                "file_type": {
                    "type": "string",
                    "description": "文件类型过滤: file（仅文件）/ folder（仅文件夹）/ all（默认）",
                    "default": "all",
                },
                "sort_by": {
                    "type": "string",
                    "description": "排序字段: name/path/size/date_modified/date_created/ext",
                    "default": "",
                },
                "ext": {
                    "type": "string",
                    "description": "文件扩展名过滤，如 py / xlsx / exe",
                    "default": "",
                },
            },
            "required": ["query"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        query: str,
        path: str = "",
        max_results: int = 100,
        regex: bool = False,
        case_sensitive: bool = False,
        whole_word: bool = False,
        file_type: str = "all",
        sort_by: str = "",
        ext: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(
                _es_search,
                query=query,
                path=path or None,
                max_results=max_results,
                regex=regex,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                file_type=file_type,
                sort_by=sort_by or None,
                ext=ext or None,
            )
            return _unwrap(result)
        except Exception as e:
            return _err(f"es_search 失败: {e}")


@dataclass
class RgSearchTool(FunctionTool):
    """文件内容搜索。ripgrep + Python fallback。"""

    name: str = "rg_search"
    description: str = (
        "【替代 astrbot_grep_tool——首选】文件内容级代码搜索引擎，查找函数引用、import 出现位置、变量使用点。"
        "不要用 astrbot_grep_tool——它返回原始 `file:line:content` 文本，无 count/truncated/files_searched，"
        "LLM 每次要手动 `split(\":\")` 解析行号且不知道结果是否被截断。"
        "优先 ripgrep（毫秒级），备 Python 纯标库扫描。file_exts 逗号分隔如 'py,js,ts'，list_files=True 只列文件名不展示匹配行。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索模式，正则或字面量"},
                "path": {"type": "string", "description": "搜索起始目录，默认当前目录"},
                "file_exts": {"type": "string", "description": "逗号分隔扩展名，如 'py,js,ts'（无点号）"},
                "max_results": {"type": "integer", "description": "最大结果数，默认 40"},
                "case_sensitive": {"type": "boolean", "description": "区分大小写"},
                "whole_word": {"type": "boolean", "description": "全词匹配"},
                "list_files": {"type": "boolean", "description": "是否只返回文件名列表"},
                "context_lines": {"type": "integer", "description": "匹配行周围展示的上下文行数，默认 0。设 2 则返回前后各 2 行", "default": 0},
            },
            "required": ["pattern"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        pattern: str,
        path: str = ".",
        file_exts: str = "",
        max_results: int = 40,
        case_sensitive: bool = False,
        whole_word: bool = False,
        list_files: bool = False,
        context_lines: int = 0,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_rg_search, pattern, path, file_exts, max_results, case_sensitive, whole_word, list_files, context_lines)
            return _unwrap(result)
        except Exception as e:
            return _err(f"rg_search 失败: {e}")


# ══ 网络 ══
@dataclass
class HttpGetTool(FunctionTool):
    """HTTP GET 请求。"""

    name: str = "http_get"
    description: str = (
        "【HTTP GET 唯一选择】轻量 HTTP 请求。"
        "不要用 astrbot_execute_shell 跑 curl——它无 SSRF（内网 IP）防护。"
        "10s 超时，返回 status + body + size，body 超 5000 字符自动截断。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "请求 URL"},
                "headers": {"type": "object", "description": "自定义请求头，可选"},
            },
            "required": ["url"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        url: str,
        headers: dict = None,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_http_get, url, headers)
            return _unwrap(result)
        except Exception as e:
            return _err(f"http_get 失败: {e}")


@dataclass
class HttpPostTool(FunctionTool):
    """HTTP POST 请求。"""

    name: str = "http_post"
    description: str = (
        "【HTTP POST 唯一选择】HTTP POST 请求。"
        "不要用 astrbot_execute_shell 跑 curl（它无 SSRF 防护）。"
        "data 为 dict 时自动 JSON 编码，str 原样发送。10s 超时。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "请求 URL"},
                "data": {
                    "type": "string",
                    "description": "POST body，dict 自动 JSON 编码，str 原样发送",
                },
                "headers": {"type": "object", "description": "自定义请求头，可选"},
            },
            "required": ["url"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        url: str,
        data: str = "",
        headers: dict = None,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            body = data
            json_failed = False
            if data:
                try:
                    parsed = json.loads(data)
                    body = parsed if isinstance(parsed, dict) else data
                except (json.JSONDecodeError, TypeError):
                    json_failed = True
            if json_failed and data.strip():
                if data.strip()[0] in ("{", "["):
                    return _err("data 看起来是 JSON 但解析失败——请检查 JSON 语法后重试")
            result = await _run_sync(_http_post, url, body if body else None, headers)
            return _unwrap(result)
        except Exception as e:
            return _err(f"http_post 失败: {e}")


@dataclass
class HttpDownloadTool(FunctionTool):
    """HTTP 二进制下载。"""

    name: str = "http_download"
    description: str = (
        "【下载文件唯一选择】下载文件。"
        "不要用 astrbot_execute_shell 跑 wget/curl -O（它无 SSRF 防护、无 500MB 上限、无路径沙箱）。"
        "支持大文件，自动处理重定向，失败自动清理。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "下载地址"},
                "path": {"type": "string", "description": "保存路径（含文件名）"},
                "overwrite": {
                    "type": "boolean",
                    "description": "是否覆盖已有文件，默认 false",
                },
                "timeout": {"type": "integer", "description": "超时秒数，默认 60"},
            },
            "required": ["url", "path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        url: str,
        path: str,
        overwrite: bool = False,
        timeout: int = 60,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_http_download, url, path, overwrite, timeout)
            return _unwrap(result)
        except Exception as e:
            return _err(f"http_download 失败: {e}")


# ══ 文本处理 ══
@dataclass
class HtmlExtractTool(FunctionTool):
    """HTML 内容提取。"""

    name: str = "html_extract"
    description: str = (
        "从 HTML 中提取结构化内容。用 BeautifulSoup + lxml。"
        "what: text(纯文本) / links(链接) / tables(表格) / query(CSS选择器)。"
        "query 模式需 selector 参数如 'div.content p'。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "HTML 字符串"},
                "what": {
                    "type": "string",
                    "description": "提取类型: text / links / tables / query",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS 选择器，what='query' 时必填",
                },
            },
            "required": ["html", "what"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        html: str,
        what: str,
        selector: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_html_extract, html, what, selector)
            return _unwrap(result)
        except Exception as e:
            return _err(f"html_extract 失败: {e}")


@dataclass
class DirTreeTool(FunctionTool):
    """目录树可视化。"""

    name: str = "dir_tree"
    description: str = (
        "【优于 dir /s——首选】目录树可视化，直接返回缩进树形文本。"
        "比 shell tree 快 10 倍，比 Python 递归简洁 5 倍，无需手动解析层级。"
        "支持 max_depth/show_hidden/pattern 过滤。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径"},
                "max_depth": {"type": "integer", "description": "最大递归深度，默认 3"},
                "show_hidden": {
                    "type": "boolean",
                    "description": "是否显示隐藏文件，默认 false",
                },
                "pattern": {"type": "string", "description": "文件名过滤，如 '*.py'"},
            },
            "required": ["path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        path: str,
        max_depth: int = 3,
        show_hidden: bool = False,
        pattern: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_dir_tree, path, max_depth, show_hidden, pattern)
            return _unwrap(result)
        except Exception as e:
            return _err(f"dir_tree 失败: {e}")


@dataclass
class DiskInfoTool(FunctionTool):
    """磁盘空间查询。"""

    name: str = "disk_info"
    description: str = (
        "查询所有磁盘分区的使用情况。返回每个盘符的 total/used/free/percent。"
        "纯 shutil 标准库。当你需要知道磁盘剩余空间时使用。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_disk_info)
            return _unwrap(result)
        except Exception as e:
            return _err(f"disk_info 失败: {e}")


# ══ 系统信息 ══
@dataclass
class PortCheckTool(FunctionTool):
    """端口检测。"""

    name: str = "port_check"
    description: str = (
        "【替代 netstat——首选】端口检测，3s 超时，直接返回布尔值+端口号。"
        "比原生 netstat 少 10 行 awk 过滤。支持单端口检测和批量扫描。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "主机地址，默认 127.0.0.1",
                    "default": "127.0.0.1",
                },
                "ports": {
                    "type": "array",
                    "description": "端口列表，如 [7860, 19530, 6199]。单端口传 [7860]",
                },
            },
            "required": ["ports"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        host: str = "127.0.0.1",
        ports: list = None,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            if not ports:
                return _err("请提供 ports 参数")
            if len(ports) == 1:
                result = await _run_sync(_port_check, host, ports[0])
            else:
                result = await _run_sync(_port_scan, ports, host)
            return _unwrap(result)
        except Exception as e:
            return _err(f"port_check 失败: {e}")


@dataclass
class FileDiffTool(FunctionTool):
    """文件差异比较。"""

    name: str = "file_diff"
    description: str = (
        "【替代 fc/diff——首选】结构化文件对比，直接返回 added/removed/total_changes。"
        "比原生 fc 多一层统计摘要，输出远比 raw diff 更适合程序处理。"
        "返回结构化差异 + unified diff（限 100 行）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "file_a": {"type": "string", "description": "第一个文件路径"},
                "file_b": {"type": "string", "description": "第二个文件路径"},
            },
            "required": ["file_a", "file_b"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        file_a: str,
        file_b: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_diff, file_a, file_b)
            return _unwrap(result)
        except Exception as e:
            return _err(f"file_diff 失败: {e}")


@dataclass
class ProcListTool(FunctionTool):
    """进程列表查询。"""

    name: str = "proc_list"
    description: str = (
        "【替代 tasklist/ps——首选】进程列表（name/pid/memory_kb），按内存降序。"
        "比原生 tasklist 多一层结构化过滤，支持 filter_name 模糊匹配。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filter_name": {
                    "type": "string",
                    "description": "按进程名模糊过滤，如 'python' 'docker' 'node'",
                }
            },
            "required": [],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], filter_name: str = "", **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_proc_list, filter_name or None)
            return _unwrap(result)
        except Exception as e:
            return _err(f"proc_list 失败: {e}")


@dataclass
class FileHashTool(FunctionTool):
    """文件哈希计算。"""

    name: str = "file_hash"
    description: str = (
        "计算文件哈希值（MD5/SHA1/SHA256）。默认 SHA256。"
        "纯 hashlib 标准库，返回 hex 字符串 + 文件大小。"
        "用于验证下载完整性、比对文件是否一致。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "algo": {
                    "type": "string",
                    "description": "哈希算法: md5/sha1/sha256，默认 sha256",
                    "default": "sha256",
                },
            },
            "required": ["filepath"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        algo: str = "sha256",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_hash, filepath, algo)
            return _unwrap(result)
        except Exception as e:
            return _err(f"file_hash 失败: {e}")


@dataclass
class FileZipTool(FunctionTool):
    """ZIP 压缩。"""

    name: str = "file_zip"
    description: str = (
        "【替代 zip——首选】打包到 ZIP，自动验证文件列表。"
        "比原生 zip 多一层失败回退。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "files": {"type": "array", "description": "要打包的文件/目录路径列表"},
                "output": {"type": "string", "description": "输出 ZIP 文件路径"},
            },
            "required": ["files", "output"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        files: list,
        output: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_zip, files, output)
            return _unwrap(result)
        except Exception as e:
            return _err(f"file_zip 失败: {e}")


@dataclass
class FileUnzipTool(FunctionTool):
    """ZIP 解压。"""

    name: str = "file_unzip"
    description: str = (
        "【替代 unzip——首选】解压 ZIP，自动防御路径穿越。"
        "比原生 unzip 多一层 Zip-slip 防护，拦截恶意压缩包。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "zip_file": {"type": "string", "description": "ZIP 文件路径"},
                "output_dir": {"type": "string", "description": "解压目标目录"},
            },
            "required": ["zip_file", "output_dir"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        zip_file: str,
        output_dir: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_file_unzip, zip_file, output_dir)
            return _unwrap(result)
        except Exception as e:
            return _err(f"file_unzip 失败: {e}")


@dataclass
class SysSnapshotTool(FunctionTool):
    """系统快照。"""

    name: str = "sys_snapshot"
    description: str = (
        "获取系统整体状态快照：主机名/平台/Python版本/CPU核数/内存总量和可用/进程数/开机时间。"
        "纯标准库 + systeminfo/tasklist。当你需要了解系统整体状况时调用。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            result = await _run_sync(_sys_snapshot)
            return _unwrap(result)
        except Exception as e:
            return _err(f"sys_snapshot 失败: {e}")


# ══ 编码 ══
@dataclass
class Base64Tool(FunctionTool):
    name: str = "base64_"
    description: str = (
        "【替代 base64 命令——首选】Base64 编解码。"
        "action: encode(编码)/decode(解码)。encode 时 as_uri=True 可生成 data: URI，"
        "decode 时 strip_uri=True 自动剥离 data: URI 前缀。"
        "比 shell base64 命令少一步管道拼接。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "encode / decode", "enum": ["encode", "decode"]},
                "data": {"type": "string", "description": "要处理的文本"},
                "as_uri": {"type": "boolean", "description": "encode 时是否生成 data: URI", "default": False},
                "strip_uri": {"type": "boolean", "description": "decode 时是否剥离 data: URI 前缀", "default": False},
            },
            "required": ["action", "data"],
        }
    )
    async def call(
        self, context: ContextWrapper[AstrAgentContext], action: str, data: str,
        as_uri: bool = False, strip_uri: bool = False, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            if action == "encode": return _unwrap(await _run_sync(b64_encode, data, as_uri))
            return _unwrap(await _run_sync(b64_decode, data, strip_uri))
        except Exception as e: return _err(f"base64_ 失败: {e}")


@dataclass
class HexTool(FunctionTool):
    name: str = "hex_"
    description: str = (
        "【替代 xxd/od——首选】十六进制与文本互转。"
        "action: encode(文本→十六进制) / decode(十六进制→文本)。比 shell xxd 少 5 个参数。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "encode / decode", "enum": ["encode", "decode"]},
                "data": {"type": "string", "description": "要处理的文本"},
            },
            "required": ["action", "data"],
        }
    )
    async def call(self, context: ContextWrapper[AstrAgentContext], action: str, data: str, **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            if action == "encode": return _unwrap(await _run_sync(hex_encode, data))
            return _unwrap(await _run_sync(hex_decode, data))
        except Exception as e: return _err(f"hex_ 失败: {e}")


@dataclass
class UrlTool(FunctionTool):
    name: str = "url_"
    description: str = "URL 编解码。action: encode(编码) / decode(解码)。比手写 urllib.parse 少 4 行样板。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "encode / decode", "enum": ["encode", "decode"]},
                "data": {"type": "string", "description": "要处理的文本"},
            },
            "required": ["action", "data"],
        }
    )
    async def call(self, context: ContextWrapper[AstrAgentContext], action: str, data: str, **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            if action == "encode": return _unwrap(await _run_sync(url_encode, data))
            return _unwrap(await _run_sync(url_decode, data))
        except Exception as e: return _err(f"url_ 失败: {e}")


# ══ 时间 ══
@dataclass
class TimeNowTool(FunctionTool):
    name: str = "time_now"
    description: str = "获取当前时间：ISO 字符串 + Unix 时间戳（秒和毫秒）。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )
    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_time_now))
        except Exception as e:
            return _err(f"time_now 失败: {e}")


@dataclass
class TimeConvertTool(FunctionTool):
    name: str = "time_convert"
    description: str = "【替代手动乘除——首选】Unix 时间戳与 ISO 互转。direction: to_iso(时间戳→ISO) / to_ts(ISO→时间戳)。ms=True 表示毫秒。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "description": "to_iso / to_ts", "enum": ["to_iso", "to_ts"]},
                "ts": {"type": "integer", "description": "时间戳（to_iso 时使用）"},
                "ms": {"type": "boolean", "description": "毫秒时间戳", "default": False},
                "iso": {"type": "string", "description": "ISO 字符串（to_ts 时使用）"},
            },
            "required": ["direction"],
        }
    )
    async def call(self, context: ContextWrapper[AstrAgentContext], direction: str, ts: int = None,
                   ms: bool = False, iso: str = "", **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            if direction == "to_iso":
                if ts is None: return _err("to_iso 需要 ts 参数")
                return _unwrap(await _run_sync(ts_to_iso, ts, ms))
            if not iso: return _err("to_ts 需要 iso 参数")
            return _unwrap(await _run_sync(iso_to_ts, iso))
        except Exception as e: return _err(f"time_convert 失败: {e}")


@dataclass
class TimeDiffTool(FunctionTool):
    name: str = "time_diff"
    description: str = "计算两个 ISO 时间的差值（秒/分/时）。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "iso1": {"type": "string", "description": "第一个 ISO 时间"},
                "iso2": {"type": "string", "description": "第二个 ISO 时间"},
            },
            "required": ["iso1", "iso2"],
        }
    )
    async def call(
        self, context: ContextWrapper[AstrAgentContext], iso1: str, iso2: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(time_diff, iso1, iso2))
        except Exception as e:
            return _err(f"time_diff 失败: {e}")


@dataclass
class RegexTestTool(FunctionTool):
    """正则测试。"""

    name: str = "regex_test"
    description: str = (
        "测试正则表达式：返回匹配项、位置(start/end)、分组信息（有名/数字）。"
        "flags 支持: i(忽略大小写) m(多行) s(DOTALL) x(VERBOSE)，可组合如 'im'。"
        "纯 re 标准库。匹配上限 50 条，超过会标记 truncated。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "正则表达式"},
                "text": {"type": "string", "description": "要匹配的文本"},
                "flags": {
                    "type": "string",
                    "description": "正则标志，如 'i' 'im' 'imsx'，可选",
                },
            },
            "required": ["pattern", "text"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        pattern: str,
        text: str,
        flags: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_regex_test, pattern, text, flags))
        except Exception as e:
            return _err(f"regex_test 失败: {e}")


@dataclass
class RegexReplaceTool(FunctionTool):
    """正则替换。"""

    name: str = "regex_replace"
    description: str = (
        "正则替换：用 replacement 替换 text 中所有匹配 pattern 的内容。"
        "支持反向引用 \\1 \\2 和有名分组 \\g<name>。"
        "flags 同 regex_test。返回替换后文本（限 5000 字符）和替换次数。"
        "纯 re 标准库。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "正则表达式（匹配规则）"},
                "replacement": {
                    "type": "string",
                    "description": "替换文本，支持 \\1 \\2 反向引用",
                },
                "text": {"type": "string", "description": "原始文本"},
                "flags": {"type": "string", "description": "正则标志，如 'i'"},
            },
            "required": ["pattern", "replacement", "text"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        pattern: str,
        replacement: str,
        text: str,
        flags: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_regex_replace, pattern, replacement, text, flags))
        except Exception as e:
            return _err(f"regex_replace 失败: {e}")


@dataclass
class DirListTool(FunctionTool):
    """列出目录内容。"""

    name: str = "dir_list"
    description: str = (
        "【优于 dir——首选】目录列表，返回结构化条目（name/size/type/date）。"
        "比 shell dir 快 10 倍，比 Python os.listdir 少 100 行样板代码。"
        "支持 pattern 通配/max_depth/show_hidden，目录优先排序，上限 200。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径"},
                "pattern": {
                    "type": "string",
                    "description": "文件名匹配，如 '*.py' 'test_*'，默认 '*'",
                },
                "max_depth": {"type": "integer", "description": "最大递归深度，默认 1"},
                "show_hidden": {
                    "type": "boolean",
                    "description": "是否显示隐藏文件，默认 false",
                },
            },
            "required": ["path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        path: str,
        pattern: str = "*",
        max_depth: int = 1,
        show_hidden: bool = False,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_list_dir, path, pattern, max_depth, show_hidden))
        except Exception as e:
            return _err(f"dir_list 失败: {e}")


@dataclass
class JsonQueryTool(FunctionTool):
    """JSON 查询。"""

    name: str = "json_query"
    description: str = (
        "jq 式 JSON 查询——点路径遍历 JSON 字符串。"
        "语法: key.subkey / key[0] / key[-1] / [*].field。"
        "用于解析 API 返回、提取嵌套字段、聚合数组元素。纯 json 标准库。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON 字符串"},
                "path": {
                    "type": "string",
                    "description": "查询路径，如 'data.items[0].name' 或 'users[*].email'",
                },
            },
            "required": ["data", "path"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], data: str, path: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_json_query, data, path))
        except Exception as e:
            return _err(f"json_query 失败: {e}")


@dataclass
class TextFilterTool(FunctionTool):
    """行文本过滤。"""

    name: str = "text_filter"
    description: str = (
        "【替代 grep——首选】行过滤器，自动切换 regex/fnmatch 双模式。"
        "比原生 grep 多 200 行截断保护，支持 grep/invert/head/tail/count。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: grep / invert / head / tail / count",
                },
                "text": {"type": "string", "description": "输入文本"},
                "pattern": {
                    "type": "string",
                    "description": "grep/invert 时的匹配模式（通配或正则）",
                },
                "n": {
                    "type": "integer",
                    "description": "head/tail 时取的行数",
                    "default": 10,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写，默认 false",
                },
                "regex": {
                    "type": "boolean",
                    "description": "是否将 pattern 视为正则表达式，默认 false",
                },
            },
            "required": ["action", "text"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        action: str,
        text: str,
        pattern: str = "",
        n: int = 10,
        case_sensitive: bool = False,
        regex: bool = False,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(
                _text_filter, text, action, pattern, n, case_sensitive, regex
            ))
        except Exception as e:
            return _err(f"text_filter 失败: {e}")


@dataclass
class DiffStringsTool(FunctionTool):
    """字符串差异比较。"""

    name: str = "diff_strings"
    description: str = (
        "比较两个字符串（非文件），返回 unified diff。"
        "纯 difflib 标准库。返回 added/removed/total_changes/identical。"
        "context_lines 控制上下文行数（默认 3）。用于比较命令输出、配置前后差异。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "第一个字符串"},
                "b": {"type": "string", "description": "第二个字符串"},
                "context_lines": {
                    "type": "integer",
                    "description": "上下文行数，默认 3",
                },
            },
            "required": ["a", "b"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        a: str,
        b: str,
        context_lines: int = 3,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_diff_strings, a, b, context_lines))
        except Exception as e:
            return _err(f"diff_strings 失败: {e}")


@dataclass
class CsvParseTool(FunctionTool):
    """CSV 解析。"""

    name: str = "csv_parse"
    description: str = (
        "解析 CSV/TSV 文本为结构化数据（dict 列表）。"
        "delimiter='auto' 自动检测分隔符（逗号或制表符）。has_header=True 时首行为表头。"
        "返回 headers + rows + count，上限 200 行。纯 csv 标准库。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "CSV/TSV 文本"},
                "delimiter": {
                    "type": "string",
                    "description": "分隔符，'auto' 自动检测，或指定 ',' '\\t'",
                },
                "has_header": {
                    "type": "boolean",
                    "description": "首行是否为表头，默认 true",
                },
            },
            "required": ["text"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        text: str,
        delimiter: str = "auto",
        has_header: bool = True,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_csv_parse, text, delimiter, has_header))
        except Exception as e:
            return _err(f"csv_parse 失败: {e}")


@dataclass
class CsvGenTool(FunctionTool):
    """CSV 生成。"""

    name: str = "csv_gen"
    description: str = (
        "将 dict 列表生成为 CSV 文本。delimiter 默认逗号。"
        '输入格式: [{"name":"a","age":1}, ...]。纯 csv 标准库。'
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "string",
                    "description": 'JSON 数组字符串，如 \'[{"a":1},{"a":2}]\'',
                },
                "delimiter": {"type": "string", "description": "分隔符，默认 ','"},
            },
            "required": ["rows"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        rows: str,
        delimiter: str = ",",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            parsed = json.loads(rows)
            return _unwrap(await _run_sync(_csv_gen, parsed, delimiter))
        except Exception as e:
            return _err(f"csv_gen 失败: {e}")


# ══ 扩展 ══
@dataclass
class UuidGenTool(FunctionTool):
    """UUID/随机字符串生成。"""

    name: str = "uuid_gen"
    description: str = (
        "生成唯一标识符或随机字符串。kind: uuid4(UUID4) / hex(十六进制) / token(字母数字)。"
        "hex/token 可设 length 控制长度（默认 16）。纯 uuid+secrets 标准库。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "description": "类型: uuid4 / hex / token",
                    "default": "uuid4",
                },
                "length": {
                    "type": "integer",
                    "description": "hex/token 时的长度，默认 16",
                },
            },
            "required": [],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        kind: str = "uuid4",
        length: int = 16,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_uuid_gen, kind, length))
        except Exception as e:
            return _err(f"uuid_gen 失败: {e}")


@dataclass
class SemverTool(FunctionTool):
    """语义版本号比较。"""

    name: str = "semver_compare"
    description: str = (
        "比较两个语义版本号。返回 > / < / =。支持 '1.2.3' '2.0.0-beta.1' 格式。"
        "纯 Python，无依赖。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "v1": {"type": "string", "description": "第一个版本号"},
                "v2": {"type": "string", "description": "第二个版本号"},
            },
            "required": ["v1", "v2"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], v1: str, v2: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_semver_compare, v1, v2))
        except Exception as e:
            return _err(f"semver_compare 失败: {e}")


@dataclass
class MdStripTool(FunctionTool):
    """Markdown 剥离。"""

    name: str = "md_strip"
    description: str = (
        "剥离 Markdown 标记，返回纯文本。处理标题/粗体/斜体/代码块/链接/图片/列表/引用/删除线。"
        "纯 re 标准库。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Markdown 文本"}},
            "required": ["text"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], text: str, **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_md_strip, text))
        except Exception as e:
            return _err(f"md_strip 失败: {e}")


@dataclass
class GhPrTool(FunctionTool):
    """GitHub Pull Request 操作。"""

    name: str = "gh_pr"
    description: str = (
        "【替代 gh CLI——首选】GitHub PR 管理。"
        "比原生 gh 多一层 --body-file 转义防护，直接返回结构化 JSON。"
        "action: create/list/merge/view。create 需 title+body；merge 需 number+strategy；view 需 number。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: create / list / merge / view",
                    "enum": ["create", "list", "merge", "view"],
                },
                "cwd": {"type": "string", "description": "仓库路径，默认当前工作目录"},
                "title": {"type": "string", "description": "PR 标题（create 时必填）"},
                "body": {"type": "string", "description": "PR 正文（create 时可选）"},
                "number": {
                    "type": "integer",
                    "description": "PR 编号（merge/view 时使用）",
                },
                "state": {
                    "type": "string",
                    "description": "list 时筛选: open/closed/merged",
                },
                "limit": {"type": "integer", "description": "list 时返回数量上限"},
                "base": {
                    "type": "string",
                    "description": "create 时目标分支，默认 master",
                },
                "head": {
                    "type": "string",
                    "description": "create 时源分支，默认当前分支",
                },
                "strategy": {
                    "type": "string",
                    "description": "merge 时合并策略: squash/rebase/merge",
                },
            },
            "required": ["action"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        action: str,
        cwd: str = "",
        title: str = "",
        body: str = "",
        number: int = 0,
        state: str = "open",
        limit: int = 10,
        base: str = "master",
        head: str = "",
        strategy: str = "squash",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            match action:
                case "create":
                    if not title:
                        return _err("gh_pr create 需要 title 参数")
                    result = await _run_sync(
                        _gh_pr_create, cwd or "", title, body, base, head
                    )
                case "list":
                    result = await _run_sync(_gh_pr_list, cwd or "", state, limit)
                case "merge":
                    result = await _run_sync(
                        _gh_pr_merge, cwd or "", number or None, strategy
                    )
                case "view":
                    result = await _run_sync(
                        _gh_pr_view, cwd or "", number or None
                    )
                case _:
                    return _err(f"未知操作: {action}")
            return _unwrap(result)
        except Exception as e:
            return _err(f"gh_pr.{action} 失败: {e}")


@dataclass
class GhIssueTool(FunctionTool):
    """GitHub Issue 操作。"""

    name: str = "gh_issue"
    description: str = (
        "【替代 gh CLI——首选】GitHub Issue 管理。"
        "比原生 gh 多一层结构化 JSON 输出。"
        "action: create/list/close。create 需 title+body；close 需 number。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: create / list / close",
                    "enum": ["create", "list", "close"],
                },
                "cwd": {"type": "string", "description": "仓库路径，默认当前工作目录"},
                "title": {
                    "type": "string",
                    "description": "Issue 标题（create 时必填）",
                },
                "body": {
                    "type": "string",
                    "description": "Issue 正文（create 时可选）",
                },
                "number": {
                    "type": "integer",
                    "description": "Issue 编号（close 时使用）",
                },
                "state": {"type": "string", "description": "list 时筛选: open/closed"},
                "limit": {"type": "integer", "description": "list 时返回数量上限"},
                "labels": {
                    "type": "string",
                    "description": "标签，逗号分隔（create/list 时可选）",
                },
            },
            "required": ["action"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        action: str,
        cwd: str = "",
        title: str = "",
        body: str = "",
        number: int = 0,
        state: str = "open",
        limit: int = 10,
        labels: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            match action:
                case "create":
                    if not title:
                        return _err("gh_issue create 需要 title 参数")
                    lbls = [l.strip() for l in labels.split(",")] if labels else None
                    result = await _run_sync(
                        _gh_issue_create, cwd or "", title, body, lbls
                    )
                case "list":
                    result = await _run_sync(
                        _gh_issue_list, cwd or "", state, limit, labels
                    )
                case "close":
                    if not number:
                        return _err("gh_issue close 需要 number 参数")
                    result = await _run_sync(_gh_issue_close, cwd or "", number)
                case _:
                    return _err(f"未知操作: {action}")
            return _unwrap(result)
        except Exception as e:
            return _err(f"gh_issue.{action} 失败: {e}")


@dataclass
class GhReleaseTool(FunctionTool):
    """GitHub Release 操作。"""

    name: str = "gh_release"
    description: str = (
        "【替代 gh CLI——首选】GitHub Release 管理。"
        "比原生 gh 多一层结构化 JSON 输出。"
        "action: create/list。create 需 tag+generate_notes。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: create / list",
                    "enum": ["create", "list"],
                },
                "cwd": {"type": "string", "description": "仓库路径，默认当前工作目录"},
                "tag": {
                    "type": "string",
                    "description": "Release 标签，如 v1.2.3（create 时必填）",
                },
                "notes": {
                    "type": "string",
                    "description": "Release 说明（create 时可选）",
                },
                "generate_notes": {
                    "type": "boolean",
                    "description": "自动生成 release notes（create 时默认 true）",
                },
                "limit": {"type": "integer", "description": "list 时返回数量上限"},
            },
            "required": ["action"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        action: str,
        cwd: str = "",
        tag: str = "",
        notes: str = "",
        generate_notes: bool = True,
        limit: int = 5,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            match action:
                case "create":
                    if not tag:
                        return _err("gh_release create 需要 tag 参数")
                    result = await _run_sync(
                        _gh_release_create, cwd or "", tag, notes, generate_notes
                    )
                case "list":
                    result = await _run_sync(_gh_release_list, cwd or "", limit)
                case _:
                    return _err(f"未知操作: {action}")
            return _unwrap(result)
        except Exception as e:
            return _err(f"gh_release.{action} 失败: {e}")


@dataclass
class GhRepoTool(FunctionTool):
    """GitHub 仓库与 CI 操作。"""

    name: str = "gh_repo"
    description: str = (
        "【替代 gh CLI——首选】GitHub 仓库与 CI 管理。"
        "比原生 gh 多一层结构化 JSON 输出。"
        "action: create/view/runs/auth。create 需 title(仓库名)。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: create / view / runs / auth",
                    "enum": ["create", "view", "runs", "auth"],
                },
                "cwd": {"type": "string", "description": "仓库路径，默认当前工作目录"},
                "title": {"type": "string", "description": "仓库名（create 时必填）"},
                "owner_repo": {
                    "type": "string",
                    "description": "仓库，格式 owner/repo（view 时可选）",
                },
                "public": {"type": "boolean", "description": "create 时是否公开仓库"},
                "limit": {"type": "integer", "description": "runs 时返回数量上限"},
            },
            "required": ["action"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        action: str,
        cwd: str = "",
        title: str = "",
        owner_repo: str = "",
        public: bool = False,
        limit: int = 5,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            match action:
                case "create":
                    if not title:
                        return _err("gh_repo create 需要 title 参数（仓库名）")
                    result = await _run_sync(
                        _gh_repo_create, title, not public, cwd or "", True
                    )
                case "view":
                    result = await _run_sync(_gh_repo_view, cwd or "", owner_repo)
                case "runs":
                    result = await _run_sync(_gh_run_list, cwd or "", limit)
                case "auth":
                    result = await _run_sync(_gh_auth_status)
                case _:
                    return _err(f"未知操作: {action}")
            return _unwrap(result)
        except Exception as e:
            return _err(f"gh_repo.{action} 失败: {e}")


@dataclass
class LogParseTool(FunctionTool):
    name: str = "log_parse"
    description: str = "解析日志文本为结构化数据。支持 Nginx/Apache 访问日志、syslog、JSON Lines。format=auto 自动检测。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "日志文本"},
                "format": {
                    "type": "string",
                    "description": "auto / nginx / apache / syslog / jsonl",
                    "default": "auto",
                },
            },
            "required": ["text"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        text: str,
        format: str = "auto",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_log_parse, text, format))
        except Exception as e:
            return _err(f"log_parse 失败: {e}")


@dataclass
class FileWatchTool(FunctionTool):
    name: str = "file_watch"
    description: str = "监控目录/文件变化（轮询 mtime/size），用于观察操作后的文件变更。duration_s 监控时长(默认10s)，interval_s 轮询间隔(默认1s)。注意会阻塞 duration_s 秒。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录或文件路径"},
                "duration_s": {
                    "type": "integer",
                    "description": "监控时长（秒），默认 10",
                },
                "interval_s": {
                    "type": "number",
                    "description": "轮询间隔（秒），默认 1.0",
                },
            },
            "required": ["path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        path: str,
        duration_s: int = 10,
        interval_s: float = 1.0,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_file_watch, path, duration_s, interval_s))
        except Exception as e:
            return _err(f"file_watch 失败: {e}")


@dataclass
class ConfigDiffTool(FunctionTool):
    name: str = "config_diff"
    description: str = (
        "比较两个 JSON/YAML 配置文件的结构化差异（按 key 比较，非逐行 diff）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "file_a": {"type": "string", "description": "第一个配置文件路径"},
                "file_b": {"type": "string", "description": "第二个配置文件路径"},
            },
            "required": ["file_a", "file_b"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        file_a: str,
        file_b: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_config_diff, file_a, file_b))
        except Exception as e:
            return _err(f"config_diff 失败: {e}")


@dataclass
class SvgRenderTool(FunctionTool):
    name: str = "svg_render"
    description: str = "将 SVG 文件渲染为 PNG，用于预览 SVG 图标/图形效果。需要 cairosvg (pip install cairosvg)。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "svg_path": {"type": "string", "description": "SVG 文件路径"},
                "output_path": {
                    "type": "string",
                    "description": "输出 PNG 路径，默认同名",
                },
            },
            "required": ["svg_path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        svg_path: str,
        output_path: str = "",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_svg_render, svg_path, output_path))
        except Exception as e:
            return _err(f"svg_render 失败: {e}")


@dataclass
class JsonSchemaValTool(FunctionTool):
    name: str = "json_schema_val"
    description: str = (
        "根据 JSON Schema 校验 JSON 数据。需要 jsonschema (pip install jsonschema)。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON 字符串（待校验数据）"},
                "schema": {
                    "type": "string",
                    "description": "JSON 字符串（Schema 定义）",
                },
            },
            "required": ["data", "schema"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        data: str,
        schema: str,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_json_schema_val, data, schema))
        except Exception as e:
            return _err(f"json_schema_val 失败: {e}")


@dataclass
class ProjectInitTool(FunctionTool):
    name: str = "project_init"
    description: str = "扫描项目目录，detect 语言/框架/依赖/目录结构，返回结构化上下文 JSON 给 LLM 理解项目。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "project_dir": {
                    "type": "string",
                    "description": "项目根目录路径，默认当前目录",
                },
            },
            "required": [],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        project_dir: str = ".",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_project_init_scan, project_dir))
        except Exception as e:
            return _err(f"project_init 失败: {e}")


@dataclass
class GitChangelogTool(FunctionTool):
    name: str = "git_changelog"
    description: str = "从 git log 生成分类 changelog：按 fix:/feat:/refactor:/docs: 前缀分组，返回结构化 counts。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "cwd": {"type": "string", "description": "Git 仓库路径"},
                "count": {
                    "type": "integer",
                    "description": "最近的 commit 数，默认 30",
                },
            },
            "required": ["cwd"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        cwd: str,
        count: int = 30,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_git_changelog, cwd, count))
        except Exception as e:
            return _err(f"git_changelog 失败: {e}")


@dataclass
class LintRunnerTool(FunctionTool):
    name: str = "lint_runner"
    description: str = (
        "代码质量检查（ruff/pylint/eslint）。"
        "与 syntax_check 配合使用：syntax_check 查能不能跑，lint_runner 查写得好不好。"
        "linter=auto 自动检测已安装的 linter（ruff→pylint→eslint）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "要检查的文件路径"},
                "linter": {
                    "type": "string",
                    "description": "linter: auto/ruff/pylint/eslint",
                    "default": "auto",
                },
            },
            "required": ["filepath"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        filepath: str,
        linter: str = "auto",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_lint_run, filepath, linter))
        except Exception as e:
            return _err(f"lint_runner 失败: {e}")


@dataclass
class ToolStatsTool(FunctionTool):
    name: str = "tool_stats"
    description: str = "查看工具调用统计：每个工具的调用次数和总调用数。纯内存计数器。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(_tool_stats_snap())
        except Exception as e:
            return _err(f"tool_stats 失败: {e}")


@dataclass
class DbQueryTool(FunctionTool):
    name: str = "db_query"
    description: str = (
        "只读查询 SQLite 数据库，不修改数据。参数化防注入，仅允许 SELECT/PRAGMA。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "SQLite 数据库文件路径"},
                "sql": {"type": "string", "description": "SELECT 或 PRAGMA 查询语句"},
                "params": {
                    "type": "array",
                    "description": '查询参数列表，如 [42, "active"]',
                },
            },
            "required": ["db_path", "sql"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        db_path: str,
        sql: str,
        params: list = None,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_db_query, db_path, sql, params))
        except Exception as e:
            return _err(f"db_query 失败: {e}")


@dataclass
class DepScanTool(FunctionTool):
    name: str = "dep_scan"
    description: str = "扫描 Python 项目 import 依赖图，检测循环引用。含超时保护。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "project_dir": {
                    "type": "string",
                    "description": "项目根目录，默认当前目录",
                },
            },
            "required": [],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        project_dir: str = ".",
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_dep_scan, project_dir))
        except Exception as e:
            return _err(f"dep_scan 失败: {e}")


@dataclass
class FileRemoveTool(FunctionTool):
    """删除文件/目录（含沙箱）。"""

    name: str = "file_remove"
    description: str = (
        "【替代 del/rmdir——首选】删除文件或目录，自带沙箱和批量确认。"
        "比 shell del 多一层路径保护，比 Python os.remove 多一层批量拦截。"
        "目录超过 50 个文件时返回提案，需 confirm=true 确认。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件或目录路径"},
                "confirm": {
                    "type": "boolean",
                    "description": "目录删除需显式确认",
                    "default": False,
                },
            },
            "required": ["path"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        path: str,
        confirm: bool = False,
        **kwargs,
    ) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_file_remove, path, confirm))
        except Exception as e:
            return _err(f"file_remove 失败: {e}")


# ══ codegraph ══
@dataclass
class CodeIndexTool(FunctionTool):
    """代码语义索引：为项目建立符号索引。"""

    name: str = "code_index"
    description: str = (
        "【首次使用必调】为项目建立代码语义索引（符号+调用关系图）。"
        "Python 零依赖；其他语言需 pip install tree-sitter + grammar。"
        "索引存储为 .codegraph/codegraph.db。增量模式按 mtime 跳过未改文件。"
        "建完之后用 code_explore 回答一切代码结构问题——不要再手动 rg_search+file_read 拼答案。"
    )
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "project_dir": {"type": "string", "description": "项目根目录路径"},
            "incremental": {"type": "boolean", "description": "增量索引（跳过未改文件），默认 false", "default": False},
        },
        "required": ["project_dir"],
    })

    async def call(self, context: ContextWrapper[AstrAgentContext], project_dir: str, incremental: bool = False, **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_code_index, project_dir, incremental))
        except Exception as e:
            return _err(f"code_index 失败: {e}")


@dataclass
class CodeExploreTool(FunctionTool):
    """代码语义探索：用自然语言或符号名查询代码库结构。"""

    name: str = "code_explore"
    description: str = (
        "【代码结构问题首选——一次调用即答案】回答一切代码库结构问题："
        "符号搜索（'safe_edit 在哪'）、调用链追踪（'从 load 到 add_llm_tools'）、"
        "架构理解（'star_manager 怎么加载插件'）。返回结构化 JSON + 自然语言总结。"
        "**先调我**——查不到时看 hint 改进查询；若符号确实不在索引中（日志文本、配置值、注释关键词），"
        "fallback 到 rg_search。需要先运行 code_index 建索引。"
    )
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "自然语言或符号名，如 'safe_edit 在哪' 或 '从 load 到 add_llm_tools 的调用链'"},
            "project_dir": {"type": "string", "description": "项目根目录，默认当前目录", "default": "."},
        },
        "required": ["query"],
    })

    async def call(self, context: ContextWrapper[AstrAgentContext], query: str, project_dir: str = ".", **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_code_explore, query, project_dir))
        except Exception as e:
            return _err(f"code_explore 失败: {e}")


@dataclass
class CodeDiffImpactTool(FunctionTool):
    """变更影响分析：改完代码后追踪波及范围。"""

    name: str = "code_diff_impact"
    description: str = (
        "【变更影响分析】改完代码后追踪波及范围。适合 commit 前检查哪些符号和文件受影响。"
        "不适合：查单个函数的调用者（用 code_explore）。基于 BFS 追踪调用者链，参数 max_depth 控制深度（默认 3）。"
    )
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "filepaths": {"type": "array", "items": {"type": "string"}, "description": "变更的文件路径列表"},
            "max_depth": {"type": "integer", "description": "BFS 最大深度，默认 3", "default": 3},
        },
        "required": ["filepaths"],
    })

    async def call(self, context: ContextWrapper[AstrAgentContext], filepaths: list, max_depth: int = 3, **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_code_diff_impact, filepaths, max_depth))
        except Exception as e:
            return _err(f"code_diff_impact 失败: {e}")


@dataclass
class CodePackTool(FunctionTool):
    """精准上下文打包：以符号为起点收集 N 层调用链源码。"""

    name: str = "code_pack"
    description: str = (
        "【精准上下文打包】以符号为起点收集 N 层调用链源码。适合修 bug 前需要完整上下文。"
        "不适合：查符号在哪定义（用 code_explore）。mode 可选 callers/callees/both，depth 控制展开层数（默认 2），上限 2000 行。"
    )
    parameters: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "目标符号名（如 'Main._heal_inactivated_tools'）"},
            "depth": {"type": "integer", "description": "展开层数，默认 2", "default": 2},
            "mode": {"type": "string", "description": "callers / callees / both，默认 both", "default": "both"},
        },
        "required": ["target"],
    })

    async def call(self, context: ContextWrapper[AstrAgentContext], target: str, depth: int = 2, mode: str = "both", **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_code_pack, target, depth, mode))
        except Exception as e:
            return _err(f"code_pack 失败: {e}")


@dataclass
class CodeStatusTool(FunctionTool):
    """索引健康检查：查看索引覆盖范围和状态。"""

    name: str = "code_status"
    description: str = (
        "【索引健康检查】查看索引覆盖范围和状态。适合 code_explore 查不到时排障。"
        "不适合：索引正常时调它——直接调 code_explore。返回文件数、符号数、边数、上次索引时间、DB 大小、FTS5 状态、缺失的 grammar。"
    )
    parameters: dict = field(default_factory=lambda: {
        "type": "object", "properties": {}, "required": [],
    })

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        _tool_stats.record(self.name)
        try:
            return _unwrap(await _run_sync(_code_status))
        except Exception as e:
            return _err(f"code_status 失败: {e}")


# ═══════════════════════════════════════════════════════════
# Tool groups and registry
# ═══════════════════════════════════════════════════════════

TOOL_GROUPS: dict[str, list[str]] = {
    "安全编辑链": [
        "safe_edit",
        "safe_rollback",
        "safe_backups",
        "file_patch",
        "file_preview",
        "syntax_check",
        "lint_runner",
    ],
    "Git & GitHub": [
        "git_status",
        "git_diff",
        "git_log",
        "git_commit",
        "git_branch",
        "git_remote",
        "git_push",
        "gh_pr",
        "gh_issue",
        "gh_release",
        "gh_repo",
    ],
    "文件系统": [
        "es_search",
        "rg_search",
        "dir_tree",
        "dir_list",
        "file_diff",
        "file_hash",
        "file_zip",
        "file_unzip",
        "disk_info",
        "file_watch",
        "file_remove",
        "config_diff",
    ],
    "系统信息": ["port_check", "proc_list", "sys_snapshot", "tool_stats"],
    "网络": ["http_get", "http_post", "http_download"],
    "文本处理": [
        "html_extract",
        "json_query",
        "text_filter",
        "diff_strings",
        "regex_test",
        "regex_replace",
        "csv_parse",
        "csv_gen",
        "md_strip",
        "log_parse",
    ],
    "编码": [
        "base64_",
        "hex_",
        "url_",
    ],
    "时间": ["time_now", "time_convert", "time_diff"],
    "扩展": [
        "svg_render",
        "json_schema_val",
        "semver_compare",
        "uuid_gen",
        "project_init",
        "git_changelog",
        "db_query",
        "dep_scan",
    ],
    "代码理解": [
        "code_index",
        "code_explore",
        "code_diff_impact",
        "code_pack",
        "code_status",
    ],
}

_ALL_TOOLS = {
    "safe_edit": SafeEditTool,
    "safe_rollback": SafeRollbackTool,
    "safe_backups": SafeBackupsTool,
    "file_patch": FilePatchTool,
    "file_preview": FilePreviewTool,
    "syntax_check": SyntaxCheckTool,
    "lint_runner": LintRunnerTool,
    "git_status": GitStatusTool,
    "git_diff": GitDiffTool,
    "git_log": GitLogTool,
    "git_commit": GitCommitTool,
    "git_branch": GitBranchTool,
    "git_remote": GitRemoteTool,
    "git_push": GitPushTool,
    "gh_pr": GhPrTool,
    "gh_issue": GhIssueTool,
    "gh_release": GhReleaseTool,
    "gh_repo": GhRepoTool,
    "es_search": EsSearchTool,
    "rg_search": RgSearchTool,
    "dir_tree": DirTreeTool,
    "dir_list": DirListTool,
    "file_diff": FileDiffTool,
    "file_hash": FileHashTool,
    "file_zip": FileZipTool,
    "file_unzip": FileUnzipTool,
    "disk_info": DiskInfoTool,
    "file_watch": FileWatchTool,
    "file_remove": FileRemoveTool,
    "config_diff": ConfigDiffTool,
    "port_check": PortCheckTool,
    "proc_list": ProcListTool,
    "sys_snapshot": SysSnapshotTool,
    "tool_stats": ToolStatsTool,
    "http_get": HttpGetTool,
    "http_post": HttpPostTool,
    "http_download": HttpDownloadTool,
    "html_extract": HtmlExtractTool,
    "json_query": JsonQueryTool,
    "text_filter": TextFilterTool,
    "diff_strings": DiffStringsTool,
    "regex_test": RegexTestTool,
    "regex_replace": RegexReplaceTool,
    "csv_parse": CsvParseTool,
    "csv_gen": CsvGenTool,
    "md_strip": MdStripTool,
    "log_parse": LogParseTool,
    "base64_": Base64Tool,
    "hex_": HexTool,
    "url_": UrlTool,
    "time_now": TimeNowTool,
    "time_convert": TimeConvertTool,
    "time_diff": TimeDiffTool,
    "svg_render": SvgRenderTool,
    "json_schema_val": JsonSchemaValTool,
    "semver_compare": SemverTool,
    "uuid_gen": UuidGenTool,
    "project_init": ProjectInitTool,
    "git_changelog": GitChangelogTool,
    "db_query": DbQueryTool,
    "dep_scan": DepScanTool,
    "code_index": CodeIndexTool,
    "code_explore": CodeExploreTool,
    "code_diff_impact": CodeDiffImpactTool,
    "code_pack": CodePackTool,
    "code_status": CodeStatusTool,
}
