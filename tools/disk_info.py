"""
disk_info — 磁盘空间查询。
Windows: 遍历 A-Z 盘符。Linux/macOS: shutil.disk_usage("/")。
"""
import os
import shutil


def info() -> dict:
    """返回所有磁盘分区信息。"""
    drives = []
    if os.name == "nt":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = f"{letter}:\\"
            try:
                usage = shutil.disk_usage(path)
                drives.append(_fmt_drive(path, usage))
            except (FileNotFoundError, OSError):
                continue
    else:
        try:
            usage = shutil.disk_usage("/")
            drives.append(_fmt_drive("/", usage))
        except OSError:
            pass

    if not drives:
        return {"ok": False, "error": "无法获取磁盘信息"}

    return {"ok": True, "drives": drives}


def _fmt_drive(path: str, usage) -> dict:
    return {
        "drive": path,
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": round(usage.used / usage.total * 100, 1),
    }
