"""
syntax_check — 语法检查工具。
改完代码后验证语法正确性。支持 Python / Nim / Go / 通用文本。
"""
import subprocess
import ast
import sys
from pathlib import Path


def check(filepath: str) -> dict:
    """
    检查文件语法。
    
    Returns:
        {"ok": true, "language": "python"} 或 {"ok": false, "errors": [...], "language": "..."}
    """
    p = Path(filepath)
    if not p.exists():
        return {"ok": False, "error": f"文件不存在: {filepath}", "language": "unknown"}
    
    suffix = p.suffix.lower()
    
    if suffix == ".py":
        return _check_python(p)
    elif suffix == ".nim":
        return _check_nim(p)
    elif suffix == ".go":
        return _check_go(p)
    elif suffix in (".js", ".ts", ".jsx", ".tsx"):
        return _check_node(p)
    else:
        return {"ok": True, "language": f"text/{suffix}", "note": "无法语法检查此类型文件，仅确认文件存在"}


def _check_python(p: Path) -> dict:
    """Python 语法检查：先用 ast.parse（无副作用），失败则用 py_compile。"""
    try:
        source = p.read_text(encoding="utf-8")
        ast.parse(source)
        return {"ok": True, "language": "python"}
    except SyntaxError as e:
        return {
            "ok": False,
            "language": "python",
            "errors": [{
                "line": e.lineno,
                "col": e.offset,
                "msg": e.msg,
                "text": e.text.strip() if e.text else ""
            }]
        }
    except Exception:
        # 回退到 py_compile
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", "--", str(p)],
                capture_output=True, text=True, timeout=10, check=True
            )
            return {"ok": True, "language": "python"}
        except subprocess.CalledProcessError as e:
            return _parse_py_compile_error(e.stderr, "python")


def _check_nim(p: Path) -> dict:
    """Nim 语法检查：nim check。"""
    try:
        result = subprocess.run(
            ["nim", "check", "--verbosity:0", "--", str(p)],
            capture_output=True, text=True, timeout=20
        )
        stderr = result.stderr.strip()
        if result.returncode == 0 and not stderr:
            return {"ok": True, "language": "nim"}
        return {
            "ok": False,
            "language": "nim",
            "errors": [{"msg": stderr or result.stdout.strip()}]
        }
    except FileNotFoundError:
        return {"ok": True, "language": "nim", "skipped": True, "reason": "nim 编译器未安装，跳过语法检查"}
    except Exception as e:
        return {"ok": False, "language": "nim", "errors": [{"msg": str(e)}]}


def _check_go(p: Path) -> dict:
    """Go 语法检查：gofmt -e。"""
    try:
        result = subprocess.run(
            ["gofmt", "-e", str(p)],
            capture_output=True, text=True, timeout=15
        )
        stderr = result.stderr.strip()
        # gofmt -e 向 stderr 输出语法错误，stdout 输出格式化结果
        if result.returncode == 0 and not stderr:
            return {"ok": True, "language": "go"}
        return {"ok": False, "language": "go", "errors": [{"msg": stderr}]}
    except FileNotFoundError:
        return {"ok": True, "language": "go", "skipped": True, "reason": "go 未安装，跳过语法检查"}
    except Exception as e:
        return {"ok": False, "language": "go", "errors": [{"msg": str(e)}]}


def _check_node(p: Path) -> dict:
    """JS/TS 语法检查：node --check。"""
    try:
        result = subprocess.run(
            ["node", "--check", "--", str(p)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {"ok": True, "language": "javascript/typescript"}
        return {"ok": False, "language": "javascript/typescript", "errors": [{"msg": result.stderr.strip()}]}
    except FileNotFoundError:
        return {"ok": True, "language": "javascript/typescript", "skipped": True, "reason": "node 未安装，跳过语法检查"}
    except Exception as e:
        return {"ok": False, "language": "javascript/typescript", "errors": [{"msg": str(e)}]}


def _parse_py_compile_error(stderr: str, language: str) -> dict:
    """解析 py_compile 的标准错误输出。"""
    errors = []
    for line in stderr.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        errors.append({"msg": line})
    return {"ok": False, "language": language, "errors": errors if errors else [{"msg": stderr}]}
