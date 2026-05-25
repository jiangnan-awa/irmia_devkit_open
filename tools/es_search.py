"""
es_search — Everything 搜索引擎封装。
使用 es.exe 进行毫秒级文件名搜索，比 os.walk/dir 快 50-500 倍。
"""
import csv
import io
import os
import shutil
import subprocess
from pathlib import Path
from .config import get_config
from ._helpers import proposal_reply


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
        return proposal_reply(False, f"Everything (es.exe) 未找到: {es_path}",
                              error=f"es.exe 不存在: {es_path}",
                              evidence={"configured": get_config().get("es_path"), "fallback": es_path},
                              options=["安装 Everything 并确保 es.exe 在 PATH 中", "配置 es_path", "回退到 dir_list"],
                              next_call={"tool": "dir_list", "params": {"path": path or "."}})

    args = [es_path]

    if regex:
        args.extend(["-r", query])
    else:
        args.append(query)

    if ext:
        args[-1] = f'{args[-1]} *.{ext}'
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
    args.extend([
        "-csv",
        "-name",
        "-path-column",
        "-size",
        "-size-format", "1",  # bytes
        "-date-modified",
    ])

    # --- 执行 ---
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return proposal_reply(False, "Everything 搜索超时 (15s)——尝试缩小搜索范围",
                              error="es.exe 搜索超时（15s）",
                              evidence={"query": query, "timeout": 15},
                              options=["缩小 path 范围", "简化 query 通配符", "回退到 dir_list"],
                              next_call={"tool": "dir_list", "params": {"path": path or "."}})
    except Exception as e:
        return proposal_reply(False, f"es.exe 执行失败",
                              error=f"es.exe 执行失败: {e}",
                              evidence={"query": query},
                              options=["检查 query 语法", "回退到 dir_list"],
                              next_call={"tool": "dir_list", "params": {"path": path or "."}})

    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or f"es.exe 返回码 {proc.returncode}"}

    # --- 解析 CSV ---
    reader = csv.DictReader(io.StringIO(proc.stdout))
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
        items.append({
            "name": name,
            "path": fpath,
            "full": str(Path(fpath) / name) if fpath else name,
            "size": size,
            "date_modified": date_mod,
        })

    return {
        "ok": True,
        "count": len(items),
        "total_size": total_size,
        "items": items,
        "proposal": f"搜索无结果 (query: {query})——尝试放宽条件或移除过滤" if len(items) == 0 else "",
    }
