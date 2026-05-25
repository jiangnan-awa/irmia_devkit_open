"""
text_filter — 行文本过滤。
head/tail/grep-like，处理已加载的文本，不依赖 shell。
"""


def filter_lines(
    text: str,
    action: str = "grep",
    pattern: str = "",
    n: int = 10,
    case_sensitive: bool = False,
) -> dict:
    """
    对文本执行行过滤操作。
    
    Args:
        text: 输入文本
        action: grep(匹配) / invert(反向匹配) / head(前N行) / tail(后N行) / count(统计行数)
        pattern: 匹配模式（grep/invert 时使用，支持 * ? 通配但不支持完整正则）
        n: head/tail 时的行数
        case_sensitive: 是否区分大小写
    """
    lines = text.split("\n")

    if action == "head":
        result_lines = lines[:n]
        return {
            "ok": True,
            "action": "head",
            "n": n,
            "matched": len(result_lines),
            "total": len(lines),
            "result": "\n".join(result_lines),
        }

    if action == "tail":
        result_lines = lines[-n:] if n < len(lines) else lines
        return {
            "ok": True,
            "action": "tail",
            "n": n,
            "matched": len(result_lines),
            "total": len(lines),
            "result": "\n".join(result_lines),
        }

    if action == "count":
        return {
            "ok": True,
            "action": "count",
            "total": len(lines),
            "non_empty": sum(1 for l in lines if l.strip()),
        }

    if action in ("grep", "invert"):
        import fnmatch
        matched = []
        for line in lines:
            target = line if case_sensitive else line.lower()
            pat = pattern if case_sensitive else pattern.lower()
            is_match = fnmatch.fnmatch(target, f"*{pat}*")
            if (action == "grep" and is_match) or (action == "invert" and not is_match):
                matched.append(line)

        return {
            "ok": True,
            "action": action,
            "pattern": pattern,
            "matched": len(matched),
            "total": len(lines),
            "result": "\n".join(matched[:200]),
            "truncated": len(matched) > 200,
        }

    return {"ok": False, "error": f"未知 action: {action}，可选: grep/invert/head/tail/count"}
