"""
_helpers — main.py 和 registry 共用的辅助函数。
"""

import asyncio
import json


def err_json(error: str) -> str:
    return json.dumps({"ok": False, "error": error}, ensure_ascii=False)


def unwrap(result: dict) -> str:
    """检测嵌套 ok:false 并展开；成功则正常包装。"""
    if not isinstance(result, dict):
        return err_json(f"工具返回了非预期类型: {type(result).__name__}")
    if result.get("ok") is False:
        return err_json(result.get("error", "未知错误"))
    return json.dumps({"ok": True, "data": result}, ensure_ascii=False)


async def run_sync(func, *args, **kwargs):
    """在默认线程池中运行同步函数，避免阻塞 AstrBot 事件循环。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def proposal_reply(
    ok: bool,
    proposal: str,
    *,
    error: str = "",
    evidence: dict = None,
    options: list = None,
    next_call: dict = None,
    **extra,
) -> dict:
    """构建统一提案协议返回。

    仅用于需要 LLM 做出选择或理解歧义的场景。
    ok:true 的正常路径不启用，保持精简。

    WARNING: next_call 是建议，LLM 应自行判断而非盲从。

    extra 中的键值平铺合并到返回 dict。
    """
    result = {"ok": ok, "proposal": proposal, **extra}
    if error:
        result["error"] = error
    if evidence:
        result["evidence"] = evidence
    if options:
        result["options"] = options
    if next_call:
        result["next_call"] = next_call
    return result
