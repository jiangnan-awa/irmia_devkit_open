"""
_helpers — main.py 和 registry 共用的辅助函数。
"""
import asyncio
import json
from typing import Any


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
