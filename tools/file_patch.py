"""
file_patch — 精确文本替换工具。
用于修改代码、修bug、调整逻辑。不要用 file_write 改已有代码——用 file_patch。
支持单次替换和全局替换。
"""
import difflib
from pathlib import Path

from ._file_utils import read_file, read_file_with_encoding


def patch(filepath: str, old: str, new: str, replace_all: bool = False) -> dict:
    """
    精确替换文件中的文本。
    
    Args:
        filepath: 文件路径
        old: 要被替换的旧文本（精确匹配）
        new: 替换后的新文本
        replace_all: 是否替换所有匹配项（默认只替换第一个）
    
    Returns:
        {"ok": true, "replaced": 1, "file": "..."} 或 {"ok": false, "error": "..."}
    """
    # C2: 拦截空 old 字符串
    if not old:
        return {"ok": False, "error": "old 参数不能为空字符串"}

    p = Path(filepath)
    if not p.exists():
        return {"ok": False, "error": f"文件不存在: {filepath}"}

    try:
        content, encoding = read_file_with_encoding(p)
    except Exception as e:
        return {"ok": False, "error": f"无法读取文件: {e}"}
    
    if old not in content:
        # 尝试给出最接近的匹配
        lines = content.split("\n")
        best = None
        best_ratio = 0
        for i, line in enumerate(lines):
            ratio = difflib.SequenceMatcher(None, old.split("\n")[0], line).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = (i + 1, line.strip()[:80])
        
        hint = ""
        if best and best_ratio > 0.3:
            hint = f" 最接近的行 #{best[0]}: {best[1]}"
        
        return {
            "ok": False,
            "error": f"旧文本在文件中未找到。{hint}",
            "hint": f"检查 old 参数是否包含完整且精确的文本片段。"
        }
    
    count = content.count(old)
    new_content = content.replace(old, new) if replace_all else content.replace(old, new, 1)
    actual_replaced = 1 if not replace_all else count
    
    p.write_text(new_content, encoding=encoding)
    
    return {
        "ok": True,
        "replaced": actual_replaced,
        "total_occurrences": count,
        "replace_all": replace_all,
        "file": str(p.absolute())
    }


def preview(filepath: str, old: str, new: str, replace_all: bool = False) -> dict:
    """预览替换效果，不实际修改文件。返回 diff。"""
    p = Path(filepath)
    if not p.exists():
        return {"ok": False, "error": f"文件不存在: {filepath}"}

    try:
        content = read_file(p)
    except Exception as e:
        return {"ok": False, "error": f"无法读取文件: {e}"}
    
    if old not in content:
        return {"ok": False, "error": "旧文本在文件中未找到"}
    
    new_content = content.replace(old, new) if replace_all else content.replace(old, new, 1)
    diff = "\n".join(difflib.unified_diff(
        content.split("\n"), new_content.split("\n"),
        fromfile=filepath, tofile=filepath + " (preview)",
        lineterm=""
    ))
    
    return {"ok": True, "diff": diff}
