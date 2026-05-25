"""
_file_utils — 文件读取共享代码。
提供 UTF-8 → GBK fallback 读取，供 safe_edit / file_patch / file_diff 内部使用。
"""
from pathlib import Path


def read_file(path: str | Path) -> str:
    """读取文件内容。先试 UTF-8，失败回退 GBK。"""
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="gbk")


def human_size(n: int) -> str:
    """字节数 → 人类可读大小。"""
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n}{unit}"
        n //= 1024
    return f"{n}TB"
