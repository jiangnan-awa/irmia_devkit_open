"""
git_changelog — Git 日志语义分组。
按 fix:/feat:/refactor: 等前缀分类 commit，输出结构化 changelog。
"""
import subprocess
import re
from pathlib import Path


def changelog(cwd: str, count: int = 30) -> dict:
    """从 git log 生成分类 changelog。

    Args:
        cwd: Git 仓库路径
        count: 最近的 commit 数量，默认 30
    """
    if not Path(cwd).is_dir():
        return {"ok": False, "error": f"不是有效目录: {cwd}"}

    try:
        r = subprocess.run(
            ["git", "log", f"-{count}", "--oneline", "--no-decorate"],
            cwd=cwd, capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return {"ok": False, "error": f"git log 失败: {r.stderr.strip()}", "cwd": cwd}
    except FileNotFoundError:
        return {"ok": False, "error": "git 未安装或不在 PATH 中"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git log 超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
    categories = {"features": [], "fixes": [], "refactors": [], "docs": [], "other": []}

    for line in lines:
        # skip the leading hash
        m = re.match(r'^\S+\s+(.*)$', line)
        msg = m.group(1) if m else line
        if re.match(r'^feat[\s(:]', msg, re.IGNORECASE):
            categories["features"].append(msg)
        elif re.match(r'^fix[\s(:]', msg, re.IGNORECASE):
            categories["fixes"].append(msg)
        elif re.match(r'^refactor[\s(:]', msg, re.IGNORECASE):
            categories["refactors"].append(msg)
        elif re.match(r'^docs[\s(:]', msg, re.IGNORECASE):
            categories["docs"].append(msg)
        else:
            categories["other"].append(msg)

    return {
        "ok": True,
        "cwd": cwd,
        "total": len(lines),
        "categories": categories,
        "counts": {k: len(v) for k, v in categories.items()},
    }
