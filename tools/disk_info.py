"""
disk_info — 磁盘空间查询。
返回每个盘符的 total/used/free，纯 shutil 标准库。
"""
import shutil


def info() -> dict:
    """返回所有磁盘分区信息。"""
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\"
        try:
            usage = shutil.disk_usage(path)
            drives.append({
                "drive": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": round(usage.used / usage.total * 100, 1),
            })
        except (FileNotFoundError, OSError):
            continue

    if not drives:
        return {"ok": False, "error": "无法获取磁盘信息"}

    return {"ok": True, "drives": drives}
