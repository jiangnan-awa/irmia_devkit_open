"""
es_search — 文件名搜索引擎封装。
Windows: Everything + es.exe 毫秒级搜索。
Linux/macOS: locate → fd → Python os.walk 三层 fallback。
"""

import csv
import fnmatch
import io
import os
import re
import shutil
from pathlib import Path
from .config import get_config
from ._helpers import proposal_reply, _run_cmd


def _get_es_path() -> str:
    """获取 es.exe 路径：配置优先 → PATH 自动查找 → 默认路径"""
    config = get_config()
    custom = config.get("es_path", "")
    if custom and os.path.exists(custom):
        return custom
    found = shutil.which("es")
    if found:
        return found
    return "es"


SORT_MAP = {
    "name": "name",
    "path": "path",
    "size": "size",
    "ext": "extension",
    "date_created": "date-created",
    "date_modified": "date-modified",
    "date_accessed": "date-accessed",
    "run_count": "run-count",
}

# Linux/macOS 跳过目录（对标 Everything 跳过系统目录）
_POSIX_SKIP_DIRS = {
    "/proc", "/sys", "/dev", "/run", "/snap", "/var/lib/lxcfs", "/var/lib/docker",
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".mypy_cache",
}

_MAX_POSIX_FILES = 10000


def _posix_search(
    query: str, path: str | None = None, max_results: int = 100,
    case_sensitive: bool = False, file_type: str = "all", ext: str | None = None,
    regex: bool = False, whole_word: bool = False, sort_by: str | None = None,
) -> dict:
    """Linux/macOS 文件名搜索：locate → fd → os.walk 三层 fallback。"""
    search_root = path or "/"

    # --- Layer 1: locate ---
    locate_path = shutil.which("locate")
    if locate_path:
        try:
            loc_query = query.replace("*", "").replace("?", "")
            if not loc_query:
                loc_query = query
            args = [locate_path, "-l", str(max_results), "-i" if not case_sensitive else "", loc_query]
            args = [a for a in args if a]
            r = _run_cmd(args, timeout=10)
            if r["ok"] and r["stdout"]:
                items = _parse_locate_output(r["stdout"], max_results, search_root,
                                              file_type, ext, case_sensitive)
                if items:
                    items = _apply_extra_filters(items, query, regex, whole_word, case_sensitive)
                    items = _apply_sort(items, sort_by, max_results)
                    return {"ok": True, "count": len(items), "total_size": 0, "items": items,
                            "engine": "locate"}
        except Exception:
            pass

    # --- Layer 2: fd ---
    fd_path = shutil.which("fd")
    if fd_path:
        try:
            args = [fd_path, "--max-results", str(max_results),
                    "--type", "f" if file_type == "file" else ("d" if file_type == "folder" else "e")]
            if ext:
                args.extend(["-e", ext])
            if case_sensitive:
                args.append("--case-sensitive")
            else:
                args.append("--ignore-case")
            if whole_word:
                args.append("-w")
            if regex:
                args.append("--regex")
            args.append(query)
            if search_root != "/":
                args.append(search_root)
            r = _run_cmd(args, timeout=15)
            if r["ok"] and r["stdout"]:
                items = _parse_locate_output(r["stdout"], max_results, search_root,
                                              file_type, ext, case_sensitive)
                if items:
                    items = _apply_sort(items, sort_by, max_results)
                    return {"ok": True, "count": len(items), "total_size": 0, "items": items,
                            "engine": "fd", "note": "Linux 搜索模式：搜索语法有限（不支持 ext: folder: 等 Everything 语法）"}
        except Exception:
            pass

    # --- Layer 3: Python os.walk ---
    return _python_fallback_search(query, search_root, max_results, case_sensitive,
                                   file_type, ext, regex, whole_word, sort_by)


_SORT_KEYS = {
    "name": "name",
    "path": "path",
    "size": "size",
    "date_modified": "date_modified",
}


def _apply_sort(items: list[dict], sort_by: str | None, max_results: int) -> list[dict]:
    """对 locate/fd 结果排序（locate 无 -s 排序，需在解析后统一处理）。"""
    if not sort_by or sort_by not in _SORT_KEYS or not items:
        return items
    key = _SORT_KEYS[sort_by]
    try:
        items.sort(key=lambda it: (it.get(key) or 0 if key in ("size",) else (it.get(key) or "")))
        if key == "size":
            items.sort(key=lambda it: it.get("size", 0), reverse=True)
    except Exception:
        pass
    return items[:max_results]


def _apply_extra_filters(
    items: list[dict], query: str, regex: bool, whole_word: bool, case_sensitive: bool
) -> list[dict]:
    """locate 只做字面子串匹配，regex/whole_word 需在 Python 侧补过滤。"""
    if not regex and not whole_word:
        return items
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern_src = query if regex else (r"\b" + re.escape(query) + r"\b")
    try:
        rx = re.compile(pattern_src, flags)
    except re.error:
        return [it for it in items if query in it["name"]]
    return [it for it in items if rx.search(it["name"])]


def _parse_locate_output(stdout: str, max_results: int, search_root: str,
                         file_type: str, ext: str, case_sensitive: bool) -> list[dict]:
    """解析 locate/fd 输出（每行一个绝对路径），转成 es_search 统一格式。"""
    items = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        p = Path(line)
        # 限定搜索目录
        if search_root != "/" and not str(p.resolve()).startswith(str(Path(search_root).resolve())):
            continue
        # 过滤文件/目录
        try:
            if file_type == "file" and not p.is_file():
                continue
            if file_type == "folder" and not p.is_dir():
                continue
        except OSError:
            continue
        # 扩展名过滤
        if ext and p.suffix.lstrip(".") != ext.lstrip("."):
            continue
        # 大小写过滤（locate -i 已处理，fd --case-sensitive 已处理）
        try:
            st = p.stat()
            size = st.st_size
            date_mod = str(st.st_mtime)
        except OSError:
            size = 0
            date_mod = ""
        items.append({
            "name": p.name,
            "path": str(p.parent),
            "full": str(p),
            "size": size,
            "date_modified": date_mod,
        })
        if len(items) >= max_results:
            break
    return items


def _python_fallback_search(query: str, search_root: str, max_results: int,
                            case_sensitive: bool, file_type: str, ext: str,
                            regex: bool = False, whole_word: bool = False,
                            sort_by: str | None = None) -> dict:
    """Python os.walk 兜底搜索（最慢，但一定可用）。"""
    items = []
    files_scanned = 0
    rp = Path(search_root).resolve()
    # 预编译匹配模式
    flags = 0 if case_sensitive else re.IGNORECASE
    name_matcher = None
    if regex:
        try:
            name_matcher = re.compile(query, flags)
        except re.error as e:
            return {"ok": False, "error": f"非法正则表达式: {e}"}
    elif whole_word:
        name_matcher = re.compile(r"\b" + re.escape(query) + r"\b", flags)
    for root, dirs, files in os.walk(search_root):
        dirs[:] = [d for d in dirs if d not in _POSIX_SKIP_DIRS and not d.startswith(".")]
        if files_scanned >= _MAX_POSIX_FILES:
            break
        entries = []
        if file_type == "folder":
            entries = dirs
        elif file_type == "file":
            entries = files
        else:
            entries = files + dirs
        for entry in entries:
            files_scanned += 1
            ep = Path(root) / entry
            try:
                st = ep.stat()
            except OSError:
                continue
            if ext and ep.suffix.lstrip(".") != ext.lstrip("."):
                continue
            name = ep.name
            if name_matcher is not None:
                if not name_matcher.search(name):
                    continue
            else:
                name_cmp = name if case_sensitive else name.lower()
                q_cmp = query if case_sensitive else query.lower()
                if q_cmp not in name_cmp and not fnmatch.fnmatch(name_cmp, q_cmp):
                    continue
            items.append({
                "name": name,
                "path": str(ep.parent),
                "full": str(ep),
                "size": st.st_size,
                "date_modified": str(st.st_mtime),
            })
            if len(items) >= max_results:
                break
        if len(items) >= max_results:
            break

    # 排序
    if sort_by and sort_by in _SORT_KEYS and items:
        items = _apply_sort(items, sort_by, max_results)

    note = ("Python 扫描模式（较慢）。"
            "Linux/macOS 建议安装 fd（apt/dnf install fd-find 或 brew install fd）或 locate（mlocate/plocate 包）；"
            "Windows 建议安装 Everything（voidtools.com）或 fd（choco install fd / winget install sharkdp.fd）")
    return {"ok": True, "count": len(items), "total_size": 0, "items": items, "engine": "python", "note": note}


def search(
    query: str,
    path: str | None = None,
    max_results: int = 100,
    regex: bool = False,
    case_sensitive: bool = False,
    whole_word: bool = False,
    file_type: str = "all",
    sort_by: str | None = None,
    ext: str | None = None,
) -> dict:
    """
    Everything 文件搜索。

    Args:
        query: 搜索关键词（支持 Everything 搜索语法，如 *.py、folder:）
        path: 限定搜索路径，None 表示全盘搜索
        max_results: 最大结果数，默认 100。设 0 表示只统计不返回列表
        regex: 使用正则表达式
        case_sensitive: 区分大小写
        whole_word: 全词匹配
        file_type: "file" / "folder" / "all"
        sort_by: name/path/size/ext/date_created/date_modified/date_accessed/run_count
        ext: 文件扩展名过滤，如 "py" "xlsx" "exe"

    Returns:
        {"ok": true, "count": 42, "total_size": 1234567, "items": [...]}
        或 {"ok": false, "error": "..."}
    """
    es_path = _get_es_path()
    if not Path(es_path).exists():
        # es.exe 不可用 → 进入跨平台 fallback（Linux/macOS 主要路径）
        return _posix_search(query, path, max_results, case_sensitive, file_type, ext,
                             regex=regex, whole_word=whole_word, sort_by=sort_by)

    args = [es_path]

    if query.startswith(("/", "-")) and not regex:
        return {"ok": False, "error": "query 不能以 / 或 - 开头（会被 es.exe 解释为选项）。regular 搜索请用 regex=True。"}

    if regex:
        args.extend(["-r", query])
    else:
        args.append(query)

    if ext and not regex:
        args[-1] = f"ext:{ext} {args[-1]}"
    if path:
        args.extend(["-path", path])

    if file_type == "file":
        args.append("/a-d")
    elif file_type == "folder":
        args.append("/ad")

    if case_sensitive:
        args.append("-case")
    if whole_word:
        args.append("-w")

    # --- 排序 ---
    if sort_by and sort_by in SORT_MAP:
        args.extend(["-sort", SORT_MAP[sort_by]])

    # --- 限制 ---
    if max_results > 0:
        args.extend(["-n", str(max_results)])

    # --- 输出格式：CSV ---
    args.extend(
        [
            "-csv",
            "-name",
            "-path-column",
            "-size",
            "-size-format",
            "1",  # bytes
            "-date-modified",
        ]
    )

    # --- 执行 ---
    proc = _run_cmd(args, timeout=15)
    if not proc["ok"]:
        err_msg = proc.get("error", "")
        if "超时" in err_msg:
            return proposal_reply(
                False,
                "Everything 搜索超时 (15s)——尝试缩小搜索范围",
                error="es.exe 搜索超时（15s）",
                evidence={"query": query, "timeout": 15},
                options=["缩小 path 范围", "简化 query 通配符", "回退到 dir_list"],
                next_call={"tool": "dir_list", "params": {"path": path or "."}},
            )
        if "不存在" in err_msg or "未安装" in err_msg:
            return proposal_reply(
                False,
                "es.exe 未找到",
                error=err_msg,
                evidence={"query": query},
                options=["检查 query 语法", "回退到 dir_list"],
                next_call={"tool": "dir_list", "params": {"path": path or "."}},
            )
        return {"ok": False, "error": proc.get("stderr", "") or f"es.exe 返回码 {proc.get('code')}"}

    # --- 解析 CSV ---
    reader = csv.DictReader(io.StringIO(proc["stdout"]))
    items = []
    total_size = 0
    for row in reader:
        name = row.get("Name", "").strip('"')
        fpath = row.get("Path", "").strip('"')
        size_str = row.get("Size", "0").strip('"')
        date_mod = row.get("Date Modified", "").strip('"')

        try:
            size = int(size_str)
        except (ValueError, TypeError):
            size = 0

        total_size += size
        items.append(
            {
                "name": name,
                "path": fpath,
                "full": str(Path(fpath) / name) if fpath else name,
                "size": size,
                "date_modified": date_mod,
            }
        )

    r = {
        "ok": True,
        "count": len(items),
        "total_size": total_size,
        "items": items,
    }
    if len(items) == 0:
        r["proposal"] = f"搜索无结果 (query: {query})——尝试放宽条件或移除过滤"
    return r
