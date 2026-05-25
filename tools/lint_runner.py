"""
lint_runner — 代码质量检查（ruff/pylint/eslint）。
与 syntax_check 互补：syntax_check 查"能不能跑"，lint_runner 查"写得好不好"。
"""
import subprocess
import json
import shutil
from pathlib import Path


def run(filepath: str, linter: str = "auto") -> dict:
    """对文件运行 linter，返回结构化 issues。

    Args:
        filepath: 文件路径
        linter: auto(检测)/ruff/pylint/eslint
    """
    p = Path(filepath)
    if not p.exists():
        return {"ok": False, "error": f"文件不存在: {filepath}"}

    if linter == "auto":
        linter = _detect(p)

    runners = {
        "ruff": _run_ruff,
        "pylint": _run_pylint,
        "eslint": _run_eslint,
    }
    runner = runners.get(linter)
    if not runner:
        return {"ok": False, "error": f"不支持的 linter: {linter}，可选: {list(runners.keys())}"}

    return runner(p)


def _detect(p: Path) -> str:
    suffix = p.suffix.lower()
    if suffix in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        if shutil.which("eslint"):
            return "eslint"
        return "eslint"  # fallback, will get "not installed" error
    if shutil.which("ruff"):
        return "ruff"
    if shutil.which("pylint"):
        return "pylint"
    return "ruff"  # roll the dice


def _run_ruff(p: Path) -> dict:
    if not shutil.which("ruff"):
        return {"ok": False, "error": "ruff 未安装，请运行: pip install ruff"}
    try:
        r = subprocess.run(
            ["ruff", "check", "--output-format", "json", str(p)],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return {"ok": True, "linter": "ruff", "issues": [], "count": 0}
        issues = json.loads(r.stdout) if r.stdout.strip() else []
        r = {"ok": True, "linter": "ruff", "issues": issues, "count": len(issues)}
        if issues:
            r["proposal"] = f"ruff发现{len(issues)}个问题"
            r["options"] = ["逐个修复", "确认是否有意为之"]
        return r
    except json.JSONDecodeError:
        return {"ok": True, "linter": "ruff", "raw": r.stdout.strip()[:2000], "count": 0}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "ruff 超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_pylint(p: Path) -> dict:
    if not shutil.which("pylint"):
        return {"ok": False, "error": "pylint 未安装，请运行: pip install pylint"}
    try:
        r = subprocess.run(
            ["pylint", "--output-format", "json", str(p)],
            capture_output=True, text=True, timeout=60
        )
        issues = json.loads(r.stdout) if r.stdout.strip() else []
        r = {"ok": True, "linter": "pylint", "issues": issues, "count": len(issues)}
        if issues:
            r["proposal"] = f"pylint发现{len(issues)}个问题"
            r["options"] = ["逐个修复", "确认是否有意为之"]
        return r
    except json.JSONDecodeError:
        return {"ok": True, "linter": "pylint", "raw": r.stdout.strip()[:2000], "count": 0}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "pylint 超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_eslint(p: Path) -> dict:
    if not shutil.which("eslint"):
        return {"ok": False, "error": "eslint 未安装，请运行: npm install -g eslint"}
    try:
        r = subprocess.run(
            ["eslint", "--format", "json", str(p)],
            capture_output=True, text=True, timeout=30
        )
        result = json.loads(r.stdout) if r.stdout.strip() else []
        if isinstance(result, list) and len(result) > 0:
            messages = result[0].get("messages", [])
            r = {"ok": True, "linter": "eslint", "issues": messages, "count": len(messages)}
            if messages:
                r["proposal"] = f"eslint发现{len(messages)}个问题"
                r["options"] = ["逐个修复", "确认是否有意为之"]
            return r
        return {"ok": True, "linter": "eslint", "issues": [], "count": 0}
    except json.JSONDecodeError:
        return {"ok": True, "linter": "eslint", "raw": r.stdout.strip()[:2000], "count": 0}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "eslint 超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
