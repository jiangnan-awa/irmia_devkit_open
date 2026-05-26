"""
proc_list — 进程列表查询。
封装 tasklist(Windows) / ps(Linux) 命令，返回结构化的进程信息。
"""

import subprocess
import os

from ._helpers import proposal_reply


def list_processes(filter_name: str | None = None) -> dict:
    """列出所有进程。可通过 filter_name 按名称模糊过滤。"""
    if os.name == "nt":
        return _list_windows(filter_name)
    return _list_posix(filter_name)


def _list_windows(filter_name: str | None) -> dict:
    """Windows: tasklist /FO CSV"""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="gbk",
            errors="replace",
        )
        if result.returncode != 0:
            return {"ok": False, "error": f"tasklist 失败: {result.stderr.strip()}"}

        processes = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip().strip('"')
            if not line:
                continue
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 5:
                name = parts[0]
                pid = parts[1]
                try:
                    mem_str = parts[4].replace(" K", "").strip()
                    mem_kb = int(mem_str)
                except (ValueError, IndexError):
                    try:
                        mem_kb = int(mem_str.replace(".", ""))
                    except ValueError:
                        try:
                            mem_kb = int(mem_str.replace(",", ""))
                        except ValueError:
                            mem_kb = 0

                if filter_name and filter_name.lower() not in name.lower():
                    continue

                processes.append(
                    {
                        "name": name,
                        "pid": int(pid) if pid.isdigit() else 0,
                        "memory_kb": mem_kb,
                    }
                )

        return {
            "ok": True,
            "count": len(processes),
            "filter": filter_name,
            "processes": sorted(processes, key=lambda p: -p["memory_kb"]),
        }
    except FileNotFoundError:
        return proposal_reply(
            False,
            "tasklist 命令不可用",
            error="tasklist 不可用",
            options=["检查系统环境", "用 sys_snapshot 替代"],
            next_call={"tool": "sys_snapshot", "params": {}},
        )
    except Exception as e:
        return proposal_reply(
            False,
            "tasklist 执行失败",
            error=str(e),
            options=["检查系统权限", "用 sys_snapshot 替代"],
            next_call={"tool": "sys_snapshot", "params": {}},
        )


def _list_posix(filter_name: str | None) -> dict:
    """Linux/macOS: ps aux（跳过表头行）"""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"ok": False, "error": f"ps 失败: {result.stderr.strip()}"}

        processes = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            # ps aux columns: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            name = parts[10] if len(parts) > 10 else parts[0]
            if filter_name and filter_name.lower() not in name.lower():
                continue
            try:
                mem_kb = int(parts[5])  # RSS in KB
            except (ValueError, IndexError):
                mem_kb = 0
            processes.append({"name": name, "pid": pid, "memory_kb": mem_kb})

        return {
            "ok": True,
            "count": len(processes),
            "filter": filter_name,
            "processes": sorted(processes, key=lambda p: -p["memory_kb"]),
        }
    except FileNotFoundError:
        return proposal_reply(
            False,
            "ps 命令不可用",
            error="ps 不可用",
            options=["检查系统环境", "用 sys_snapshot 替代"],
            next_call={"tool": "sys_snapshot", "params": {}},
        )
    except Exception as e:
        return proposal_reply(
            False,
            "ps 执行失败",
            error=str(e),
            options=["检查系统权限", "用 sys_snapshot 替代"],
            next_call={"tool": "sys_snapshot", "params": {}},
        )
