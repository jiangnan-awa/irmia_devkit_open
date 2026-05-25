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
    regex: bool = False,
) -> dict:
    """
    对文本执行行过滤操作。

    Args:
        text: 输入文本
        action: grep(匹配) / invert(反向匹配) / head(前N行) / tail(后N行) / count(统计行数)
        pattern: 匹配模式。regex=False 时用 fnmatch 通配(*?)，regex=True 时用正则
        n: head/tail 时的行数
        case_sensitive: 是否区分大小写
        regex: 是否将 pattern 视为正则表达式
    """
    lines = text.split("\n")

    if action == "head":
        result_lines = lines[:n]
        return {
            "ok": True, "action": "head", "n": n,
            "matched": len(result_lines), "total": len(lines),
            "result": "\n".join(result_lines),
        }

    if action == "tail":
        result_lines = lines[-n:] if n < len(lines) else lines
        return {
            "ok": True, "action": "tail", "n": n,
            "matched": len(result_lines), "total": len(lines),
            "result": "\n".join(result_lines),
        }

    if action == "count":
        return {
            "ok": True, "action": "count",
            "total": len(lines),
            "non_empty": sum(1 for l in lines if l.strip()),
        }

    if action in ("grep", "invert"):
        if regex:
            import re
            flag = 0 if case_sensitive else re.IGNORECASE
            try:
                compiled = re.compile(pattern, flag)
            except re.error as e:
                return {"ok": False, "error": f"正则语法错误: {e.msg}"}
            matched = [line for line in lines if compiled.search(line)]
        else:
            import fnmatch
            matched = []
            for line in lines:
                target = line if case_sensitive else line.lower()
                pat = pattern if case_sensitive else pattern.lower()
                is_match = fnmatch.fnmatch(target, f"*{pat}*")
                if is_match:
                    matched.append(line)
        if action == "invert":
            matched_set = set(matched)
            matched = [l for l in lines if l not in matched_set]

        return {
            "ok": True,
            "action": action,
            "pattern": pattern,
            "regex": regex,
            "matched": len(matched),
            "total": len(lines),
            "result": "\n".join(matched[:200]),
            "truncated": len(matched) > 200,
        }

    return {"ok": False, "error": f"未知 action: {action}，可选: grep/invert/head/tail/count"}
