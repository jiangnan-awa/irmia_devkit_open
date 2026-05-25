"""
git_smart — Git 操作封装。
常用 git 命令的结构化输出。不要用 shell 直接执行 git 命令——用此工具。
"""
import subprocess
from pathlib import Path


def _run_git(cwd: str, args: list[str], timeout: int = 15) -> dict:
    """执行 git 命令，返回结构化结果。"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode
        }
    except FileNotFoundError:
        return {"ok": False, "error": "git 未安装或不在 PATH 中"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"git 命令超时 ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def status(cwd: str) -> dict:
    """查看仓库状态。改代码前必调，确认工作区干净。"""
    r = _run_git(cwd, ["status", "--porcelain"])
    if not r["ok"]:
        return r
    lines = r["stdout"].split("\n") if r["stdout"] else []
    return {
        "ok": True,
        "clean": len(lines) == 0 or (len(lines) == 1 and lines[0] == ""),
        "changes": [line for line in lines if line.strip()],
        "changed_count": len([l for l in lines if l.strip()])
    }


def diff(cwd: str, staged: bool = False, filepath: str = None) -> dict:
    """查看差异。提交前必调用 --staged。"""
    args = ["diff"]
    if staged:
        args.append("--staged")
    if filepath:
        args.append("--")
        args.append(filepath)
    return _run_git(cwd, args)


def log(cwd: str, count: int = 5) -> dict:
    """查看最近提交记录。"""
    r = _run_git(cwd, ["log", f"-{count}", "--oneline", "--decorate"])
    if not r["ok"]:
        return r
    return {
        "ok": True,
        "commits": r["stdout"].split("\n") if r["stdout"] else []
    }


def commit(cwd: str, message: str) -> dict:
    """提交所有更改。提交前必调 diff --staged 自查。"""
    s = status(cwd)
    if not s.get("ok"):
        return {"ok": False, "error": f"无法获取状态: {s.get('error', '未知')}"}
    if s.get("clean"):
        return {"ok": False, "error": "没有可提交的更改"}
    
    changed = s.get("changed_count", 0)
    if changed > 10:
        return {
            "ok": False,
            "error": f"未暂存文件过多 ({changed} 个)。请先用 git_status 和 git_diff 确认后分批提交。"
        }

    files_to_stage = s.get("changes", [])

    r1 = _run_git(cwd, ["add", "-A"])
    if not r1["ok"]:
        return {"ok": False, "error": f"git add 失败: {r1['stderr']}"}
    
    r2 = _run_git(cwd, ["commit", "-m", message], timeout=30)
    if not r2["ok"]:
        return {"ok": False, "error": f"git commit 失败: {r2['stderr']}"}
    
    return {
        "ok": True,
        "message": message,
        "output": r2["stdout"],
        "files_committed": changed,
        "files_staged": files_to_stage,
    }


def current_branch(cwd: str) -> dict:
    """获取当前分支名。"""
    r = _run_git(cwd, ["branch", "--show-current"])
    if not r["ok"]:
        return r
    return {"ok": True, "branch": r["stdout"]}


def remote_url(cwd: str) -> dict:
    """获取远程仓库 URL。"""
    r = _run_git(cwd, ["remote", "get-url", "origin"])
    if not r["ok"]:
        return r
    return {"ok": True, "url": r["stdout"]}


def push(cwd: str, remote: str = "origin", branch: str = "") -> dict:
    """推送到远程仓库。推送前请先用 git_status + git_diff 自查。"""
    if not branch:
        b = current_branch(cwd)
        if not b.get("ok"):
            return {"ok": False, "error": f"无法获取当前分支: {b.get('error')}"}
        branch = b["branch"]
    
    # 检查是否有未推送的 commit（远程分支不存在时跳过，由后续 push 自己报错）
    r_check = _run_git(cwd, ["log", f"origin/{branch}..HEAD", "--oneline"])
    if r_check["ok"]:
        if not r_check["stdout"].strip():
            return {"ok": False, "error": "没有未推送的提交——所有 commit 已在远程"}
    
    args = ["push", remote, branch]
    return _run_git(cwd, args, timeout=30)
