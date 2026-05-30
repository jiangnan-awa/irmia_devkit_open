"""
_file_utils — 文件读取共享代码。
提供 UTF-8 → GBK fallback 读取，供 safe_edit / file_patch / file_diff 内部使用。
"""

import difflib
from pathlib import Path


SAFE_EDIT_MAX_SIZE = 20 * 1024 * 1024
FILE_DIFF_MAX_SIZE = 50 * 1024 * 1024


def _detect_encoding(path: str | Path) -> str:
    """检测文件编码：优先 UTF-8，失败回退 GBK。"""
    p = Path(path)
    try:
        p.read_text(encoding="utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "gbk"


def read_file(path: str | Path) -> str:
    """读取文件内容。先试 UTF-8，失败回退 GBK。"""
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="gbk")


def read_file_with_encoding(path: str | Path) -> tuple[str, str]:
    """读取文件内容，同时返回检测到的编码。"""
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8"), "utf-8"
    except UnicodeDecodeError:
        return p.read_text(encoding="gbk"), "gbk"


def human_size(n: int) -> str:
    """字节数 → 人类可读大小（保留一位小数，整数则省略小数）。"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            s = f"{n:.1f}{unit}"
            return s.replace(".0", "") if ".0" in s else s
        n /= 1024
    return f"{n:.1f}PB"


def find_closest_line(content: str, old: str, threshold: float = 0.3) -> dict | None:
    """在 content 中找与 old 首行最接近的匹配行，返回行号和文本。"""
    lines = content.split("\n")
    best = None
    best_ratio = 0
    first_line = old.split("\n")[0]
    for i, line in enumerate(lines):
        ratio = difflib.SequenceMatcher(None, first_line, line).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = (i + 1, line.strip()[:80])
    if best and best_ratio > threshold:
        return {"line": best[0], "text": best[1]}
    return None
