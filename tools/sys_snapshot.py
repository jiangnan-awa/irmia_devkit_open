"""
sys_snapshot — 系统快照。
CPU/内存/磁盘/进程数/开机时长，纯标准库。
"""
import os
import platform
import subprocess
from datetime import datetime


def snapshot() -> dict:
    """获取系统整体状态快照。"""

    info = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "time": datetime.now().isoformat(),
    }

    # CPU 核心数
    try:
        info["cpu_cores"] = os.cpu_count()
    except Exception:
        info["cpu_cores"] = None

    # 内存（通过 systeminfo 提取）
    try:
        result = subprocess.run(
            ["systeminfo"],
            capture_output=True, text=True, timeout=15, encoding="gbk", errors="replace"
        )
        for line in result.stdout.split("\n"):
            line = line.strip()
            if "物理内存总量" in line:
                info["total_memory_mb"] = _extract_mb(line)
            if "可用的物理内存" in line:
                info["available_memory_mb"] = _extract_mb(line)
            if "系统启动时间" in line:
                info["boot_time"] = line.split(":", 1)[-1].strip()
    except Exception:
        info["total_memory_mb"] = None
        info["available_memory_mb"] = None

    # 进程数
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10, encoding="gbk", errors="replace"
        )
        info["process_count"] = len([l for l in result.stdout.split("\n") if l.strip()])
    except Exception:
        info["process_count"] = None

    return {"ok": True, "info": info}


def _extract_mb(line: str) -> int | None:
    """从 systeminfo 行提取内存 MB 数。"""
    try:
        parts = line.replace(",", "").split()
        for i, p in enumerate(parts):
            if "MB" in p:
                return int(parts[i - 1]) if i > 0 else None
        return None
    except Exception:
        return None
