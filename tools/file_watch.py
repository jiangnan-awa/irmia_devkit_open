"""
file_watch — 文件变化监控。
轮询 mtime/size，返回变更事件列表。不依赖 inotify/Watchdog。
"""
import os
import time
from pathlib import Path


def watch(path: str, duration_s: int = 10, interval_s: float = 1.0, pattern: str = "") -> dict:
    """监控目录/文件变化。

    Args:
        path: 目录或文件路径
        duration_s: 监控时长（秒），默认 10
        interval_s: 轮询间隔（秒），默认 1.0
        pattern: 文件名通配，如 "*.py"
    """
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"路径不存在: {path}"}

    target = [p] if p.is_file() else list(p.rglob("*") if not pattern else p.rglob(pattern))
    target = [f for f in target if f.is_file()]

    baseline = {}
    for f in target:
        try:
            st = f.stat()
            baseline[str(f)] = (st.st_mtime, st.st_size)
        except OSError:
            pass

    events = []
    start = time.time()
    deadline = start + duration_s
    while time.time() < deadline:
        time.sleep(interval_s)
        # Q2: 每轮重扫目录，捕获新增文件
        if p.is_dir():
            current_files = set(p.rglob("*") if not pattern else p.rglob(pattern))
            target = [f for f in current_files if f.is_file()]
            for f in target:
                key = str(f)
                if key not in baseline:
                    baseline[key] = (0, 0)
        for f in list(target):
            try:
                st = f.stat()
                key = str(f)
                old_mtime, old_size = baseline.get(key, (0, 0))
                if st.st_mtime != old_mtime:
                    action = "created" if old_mtime == 0 else "modified"
                    events.append({
                        "file": key,
                        "action": action,
                        "size": st.st_size,
                        "size_delta": st.st_size - old_size,
                    })
                    baseline[key] = (st.st_mtime, st.st_size)
            except FileNotFoundError:
                if str(f) in baseline:
                    events.append({"file": str(f), "action": "deleted"})
                    del baseline[str(f)]
                    target.remove(f)
            except OSError:
                pass

    return {
        "ok": True,
        "path": str(p),
        "files_watched": len(target),
        "duration_s": round(time.time() - start, 1),
        "events": events[:100],
        "event_count": len(events),
        "truncated": len(events) > 100,
    }
