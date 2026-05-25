"""
gh_cli — GitHub CLI 封装。
通过 gh 命令直接操作 GitHub，无需浏览器。
"""
import subprocess
import json
import os
import shutil
import tempfile

from .config import get_config


def _find_gh() -> str:
    """查找 gh CLI 路径。先读配置，再自动搜索 PATH。"""
    config = get_config()
    custom = config.get("gh_path", "")
    if custom and os.path.exists(custom):
        return custom
    path = shutil.which("gh")
    if path:
        return path
    return "gh"


def _run_gh(args: list[str], cwd: str = None, timeout: int = 20) -> dict:
    """执行 gh 命令，返回结构化结果。"""
    if not cwd:
        cwd = os.getcwd()
    gh_bin = _find_gh()
    try:
        result = subprocess.run(
            [gh_bin] + args,
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
        return {"ok": False, "error": f"gh 未找到: {gh_bin}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"gh 命令超时 ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pr_create(cwd: str, title: str, body: str = "", base: str = "master", head: str = "") -> dict:
    """创建 Pull Request。"""
    args = ["pr", "create", "--title", title, "--base", base]
    body_file = None
    if body:
        body_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        body_file.write(body)
        body_file.close()
        args.extend(["--body-file", body_file.name])
    if head:
        args.extend(["--head", head])
    result = _run_gh(args, cwd=cwd, timeout=30)
    if body_file:
        try:
            os.unlink(body_file.name)
        except OSError:
            pass
    return result


def pr_list(cwd: str, state: str = "open", limit: int = 10) -> dict:
    """列出 PR。"""
    r = _run_gh(
        ["pr", "list", "--state", state, "--limit", str(limit),
         "--json", "number,title,state,url,author,createdAt"],
        cwd=cwd
    )
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"])
        return {"ok": True, "prs": data, "count": len(data)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": r["stdout"]}


def pr_view(cwd: str, number: int = None) -> dict:
    """查看 PR 详情。"""
    args = ["pr", "view"]
    if number:
        args.append(str(number))
    args.extend(["--json", "number,title,state,url,body,author,createdAt,mergedAt,mergeable"])
    return _run_gh(args, cwd=cwd)


def pr_merge(cwd: str, number: int = None, strategy: str = "squash") -> dict:
    """合并 PR。strategy: squash / rebase / merge。"""
    args = ["pr", "merge"]
    if number:
        args.append(str(number))
    args.append(f"--{strategy}")
    return _run_gh(args, cwd=cwd, timeout=30)


def issue_create(cwd: str, title: str, body: str = "", labels: list[str] = None) -> dict:
    """创建 Issue。"""
    args = ["issue", "create", "--title", title]
    body_file = None
    if body:
        body_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        body_file.write(body)
        body_file.close()
        args.extend(["--body-file", body_file.name])
    if labels:
        for label in labels:
            args.extend(["--label", label])
    result = _run_gh(args, cwd=cwd, timeout=30)
    if body_file:
        try:
            os.unlink(body_file.name)
        except OSError:
            pass
    return result


def issue_list(cwd: str, state: str = "open", limit: int = 10, labels: str = "") -> dict:
    """列出 Issue。"""
    args = ["issue", "list", "--state", state, "--limit", str(limit),
            "--json", "number,title,state,url,labels,createdAt"]
    if labels:
        args.extend(["--label", labels])
    r = _run_gh(args, cwd=cwd)
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"])
        return {"ok": True, "issues": data, "count": len(data)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": r["stdout"]}


def issue_close(cwd: str, number: int) -> dict:
    """关闭 Issue。"""
    return _run_gh(["issue", "close", str(number)], cwd=cwd)


def release_create(cwd: str, tag: str, notes: str = "", generate_notes: bool = True) -> dict:
    """创建 Release。"""
    args = ["release", "create", tag]
    if generate_notes:
        args.append("--generate-notes")
    notes_file = None
    if notes:
        notes_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        notes_file.write(notes)
        notes_file.close()
        args.extend(["--notes-file", notes_file.name])
    result = _run_gh(args, cwd=cwd, timeout=30)
    if notes_file:
        try:
            os.unlink(notes_file.name)
        except OSError:
            pass
    return result


def release_list(cwd: str, limit: int = 5) -> dict:
    """列出 Release。"""
    r = _run_gh(
        ["release", "list", "--limit", str(limit),
         "--json", "name,tagName,publishedAt,isLatest,isPrerelease"],
        cwd=cwd
    )
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"])
        return {"ok": True, "releases": data, "count": len(data)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": r["stdout"]}


def repo_view(cwd: str, owner_repo: str = "") -> dict:
    """查看仓库信息。"""
    args = ["repo", "view"]
    if owner_repo:
        args.append(owner_repo)
    args.extend(["--json", "name,description,url,defaultBranchRef,stargazerCount,forkCount"])
    return _run_gh(args, cwd=cwd)


def run_list(cwd: str, limit: int = 5) -> dict:
    """查看 CI 运行记录。"""
    r = _run_gh(
        ["run", "list", "--limit", str(limit),
         "--json", "name,status,conclusion,createdAt,headBranch,url"],
        cwd=cwd
    )
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"])
        return {"ok": True, "runs": data, "count": len(data)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": r["stdout"]}


def repo_create(name: str, private: bool = True, cwd: str = "", push: bool = True) -> dict:
    """创建 GitHub 仓库并推送。"""
    args = ["repo", "create", name]
    if private:
        args.append("--private")
    else:
        args.append("--public")
    if cwd:
        args.extend(["--source", cwd, "--remote", "origin"])
        if push:
            args.append("--push")
    return _run_gh(args, cwd=cwd if cwd else None, timeout=30)


def auth_status() -> dict:
    """检查 gh 认证状态。"""
    return _run_gh(["auth", "status"])
