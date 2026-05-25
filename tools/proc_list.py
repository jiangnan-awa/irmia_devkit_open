"""
proc_list — 进程列表查询。
封装 tasklist 命令，返回结构化的进程信息。
"""
import subprocess


def list_processes(filter_name: str | None = None) -> dict:
    """列出所有进程。可通过 filter_name 按名称模糊过滤。"""
    try:
        # tasklist /FO CSV /NH 输出 CSV 无表头
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10, encoding="gbk", errors="replace"
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
                    # H10: 兼容不同语言环境的千位分隔符（逗号/点）
                    mem_str = parts[4].replace(" K", "").strip()
                    # 先尝试直接转换（无分隔符）
                    mem_kb = int(mem_str)
                except (ValueError, IndexError):
                    try:
                        # 尝试剥离点分隔符（德语等）
                        mem_kb = int(mem_str.replace(".", ""))
                    except ValueError:
                        try:
                            # 尝试剥离逗号分隔符（英语等）
                            mem_kb = int(mem_str.replace(",", ""))
                        except ValueError:
                            # 中文系统可能输出"暂缺"等非数字
                            mem_kb = 0

                if filter_name and filter_name.lower() not in name.lower():
                    continue

                processes.append({
                    "name": name,
                    "pid": int(pid) if pid.isdigit() else 0,
                    "memory_kb": mem_kb,
                })

        return {
            "ok": True,
            "count": len(processes),
            "filter": filter_name,
            "processes": sorted(processes, key=lambda p: -p["memory_kb"]),  # 按内存降序
        }
    except FileNotFoundError:
        return {"ok": False, "error": "tasklist 不可用"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
