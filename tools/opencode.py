"""
opencode — OpenCode CLI 封装。
委托编码/审查/分析任务给 OpenCode CLI。默认 DeepSeek V4 Pro，默认只读分析（audit）模式。
支持异步模式：写 task 文件到庄园任务目录，由 task_runner 消费，弥亚不阻塞。
"""
import subprocess
import os
import shutil
import json
import uuid
from datetime import datetime

from .config import get_config, get_plugin_dir


def _find_opencode() -> str:
    """查找 opencode CLI 路径。"""
    config = get_config()
    custom = config.get("opencode_path", "")
    if custom and os.path.exists(custom):
        return custom
    path = shutil.which("opencode")
    if path:
        return path
    return "opencode"


def _safe_truncate(text: str, max_chars: int = 5000) -> tuple[str, bool]:
    """按段落边界截断，保留完整行。"""
    if len(text) <= max_chars:
        return text, False
    # 在 max_chars 内找最后一个换行符
    cut = text.rfind("\n", 0, max_chars)
    if cut == -1:
        cut = max_chars  # 找不到换行，硬截
    return text[:cut], True



def _read_locks(state_dir: str = "") -> list[str]:
    """读取文件锁列表，返回被锁的文件路径。"""
    config = get_config()
    lock_dirs = config.get("lock_dirs", [])
    if not lock_dirs and not state_dir:
        return []
    candidates = []
    if state_dir and os.path.isdir(state_dir):
        candidates.append(state_dir)
    for d in lock_dirs:
        if d and os.path.isdir(d):
            candidates.append(d)
    locks = []
    for d in candidates:
        import glob as _glob
        for lockfile in _glob.glob(os.path.join(d, "*.lock")):
            try:
                with open(lockfile, "r", encoding="utf-8") as lf:
                    data = json.load(lf)
                locked_path = data.get("path") or data.get("file")
                if locked_path:
                    locks.append(locked_path)
            except Exception:
                locks.append(os.path.basename(lockfile).replace(".lock", ""))
        if locks:
            break
    return locks

def run(task: str, cwd: str = "", model: str = "opencode-go/deepseek-v4-pro",
        timeout: int = 180, mode: str = "audit", context: str = "",
        async_mode: bool = True, depends_on: str = "", files: str = "") -> dict:
    """
    委托编码/审查/分析任务给 OpenCode CLI。默认只读分析，安全优先。

    【模式选择铁律】
    - 代码审查、安全审计、项目分析 → audit（只读，不改文件）
    - 编码实现、修 bug、改文件 → code（允许修改）
    - 陌生项目先了解结构 → explore
    不明确时默认 audit，比误用 code 安全。

    Args:
        task: 任务描述（必填，越详细越好）
        cwd: 工作目录，默认当前 workspace
        model: 模型，默认 DeepSeek V4 Pro。格式 provider/model
        timeout: 超时秒数，默认 180
        mode: audit(只读分析)/code(允许修改)/explore(探索项目)，默认 audit
        context: 已知上下文（已读文件内容等），节省探索时间
        async_mode: 异步模式（默认 true）：写任务文件后立即返回，由 task_runner 后台执行。弥亚不阻塞
        depends_on: 依赖的前置任务 ID——task_runner 自动读取其结果并注入为当前任务上下文
        files: 本任务会修改的文件（逗号分隔，如 'main.py,utils.py'）。系统自动检测文件锁冲突

    Returns:
        同步: {"ok": true, "stdout": "...", ...}
        异步: {"ok": true, "queued": true, "task_id": "task_..."}
        冲突: {"ok": true, "conflict": true, "locked_files": [...], "task_id": "..."}
    """
    if not task or not task.strip():
        return {"ok": False, "error": "task 不能为空"}

    cwd = cwd or os.getcwd()
    if not os.path.isdir(cwd):
        return {"ok": False, "error": f"工作目录不存在: {cwd}"}

    if mode not in ("audit", "code", "explore"):
        return {"ok": False, "error": f"无效 mode: {mode}，可选 audit/code/explore"}

    # F3 + 锁联动：缓存 _read_locks 结果，避免重复扫描文件系统
    file_list = [f.strip() for f in files.split(",") if f.strip()] if files else []
    locks = _read_locks()

    # F3: 文件冲突检测 — 计划修改的文件是否已被弥亚锁定？
    if file_list and async_mode:
        locked_conflicts = [f for f in file_list if any(f in lock for lock in locks)]
        if locked_conflicts:
            return {
                "ok": True,
                "conflict": True,
                "locked_files": locked_conflicts,
                "hint": "以下文件已被锁定（弥亚正在编辑），请等她完成后再提交任务",
            }

    # 文件锁联动 — 注入 context 告知锻七哪些文件勿改
    if locks:
        lock_note = "以下文件已被庄园锁定（勿改）：\n" + "\n".join(f"- {l}" for l in locks[:20])
        context = lock_note + "\n\n" + (context or "")

    # ── 异步模式：写 task 文件，由 task_runner 消费 ──
    if async_mode:
        config = get_config()
        state_dir = config.get("state_dir", "")
        if state_dir and os.path.isdir(state_dir):
            task_dir = state_dir
        else:
            plug_dir = get_plugin_dir()
            if plug_dir:
                task_dir = os.path.join(str(plug_dir), "state", "tasks")
            else:
                task_dir = os.path.join(os.path.dirname(cwd), "state", "tasks")
        os.makedirs(task_dir, exist_ok=True)
        tid = datetime.now().strftime("task_%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:4]}"
        task_obj = {
            "id": tid,
            "task": task.strip(),
            "cwd": cwd,
            "context": context.strip() if context else "",
            "mode": mode,
            "model": model,
            "from": "miria",
            "to": "opencode",
            "depends_on": depends_on.strip() if depends_on else "",
            "files": file_list,
            "created": datetime.now().isoformat(),
            "status": "queued"
        }
        task_path = os.path.join(task_dir, f"{tid}.json")
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(task_obj, f, ensure_ascii=False, indent=2)
        return {
            "ok": True,
            "queued": True,
            "task_id": tid,
            "task_file": task_path,
            "mode": mode,
        }

    # ── 同步模式：直接执行 opencode CLI ──
    mode_hints = {
        "audit": "[模式: 只读分析，不要修改任何文件] ",
        "code": "[模式: 允许修改文件] ",
        "explore": "[模式: 探索项目结构，输出发现] ",
    }
    prefix = mode_hints[mode]
    if context and context.strip():
        prefix += f"已知上下文:\n{context.strip()}\n\n"
    full_task = prefix + task.strip()

    bin_path = _find_opencode()
    cmd = [bin_path, "run", "-m", model, full_task]

    safe_env = {}
    for key in ("PATH", "HOME", "USERPROFILE", "TEMP", "TMP", "SYSTEMROOT",
                 "SystemRoot", "NO_COLOR", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE",
                 "HOMEPATH", "COMSPEC", "PATHEXT", "PROCESSOR_ARCHITECTURE",
                 "NUMBER_OF_PROCESSORS", "OS", "USERNAME", "COMPUTERNAME"):
        if key in os.environ:
            safe_env[key] = os.environ[key]

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"opencode 未找到: {bin_path}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"opencode 超时 ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": f"opencode 执行异常: {e}"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        return {
            "ok": False,
            "error": stderr or stdout[:500] or f"opencode 退出码 {result.returncode}",
            "stdout_tail": stdout[:1000] if stdout else "",
        }

    out_text, truncated = _safe_truncate(stdout)
    return {
        "ok": True,
        "stdout": out_text,
        "truncated": truncated,
        "model": model,
        "cwd": cwd,
        "mode": mode,
    }
