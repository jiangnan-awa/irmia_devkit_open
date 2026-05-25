"""
regex_tester — 正则调试器。
测试正则表达式，返回匹配组、位置和纯文本解释。
纯 re 标准库，不依赖外部工具。
"""
import re
import signal

# C6: 防护限制
_MAX_PATTERN_LEN = 2000
_MAX_TEXT_LEN = 100_000
_REGEX_TIMEOUT = 3  # 秒


def _timeout_handler(signum, frame):
    raise TimeoutError("正则匹配超时")


def test(pattern: str, text: str, flags: str = "") -> dict:
    """在 text 中匹配 pattern，返回所有匹配项及分组信息。"""
    # C6: 长度限制
    if len(pattern) > _MAX_PATTERN_LEN:
        return {"ok": False, "error": f"正则表达式过长（{len(pattern)} > {_MAX_PATTERN_LEN}）"}
    if len(text) > _MAX_TEXT_LEN:
        return {"ok": False, "error": f"待匹配文本过长（{len(text)} > {_MAX_TEXT_LEN}）"}

    flag_map = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
        "x": re.VERBOSE,
    }

    re_flags = 0
    for ch in flags:
        if ch in flag_map:
            re_flags |= flag_map[ch]
        else:
            return {"ok": False, "error": f"不支持的 flag: '{ch}'，可选: {list(flag_map.keys())}"}

    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as e:
        return {"ok": False, "error": f"正则语法错误: {e.msg} (pos {e.pos})", "pattern": pattern}

    # C6: 超时保护（Unix 用 signal，Windows 用简单最大匹配数限制）
    matches = []
    try:
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(_REGEX_TIMEOUT)
        for m in compiled.finditer(text):
            match_info = {
                "match": m.group(0),
                "start": m.start(),
                "end": m.end(),
            }
            if compiled.groupindex:
                match_info["groups"] = m.groupdict()
            elif compiled.groups > 0:
                match_info["groups"] = {str(i): g for i, g in enumerate(m.groups(), 1)}
            matches.append(match_info)
            # C6: 最大匹配数保护（Windows fallback）
            if len(matches) >= 500:
                break
    except TimeoutError:
        matches.append({"match": "[TIMEOUT]", "start": -1, "end": -1})
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)

    return {
        "ok": True,
        "pattern": pattern,
        "flags": flags or "无",
        "count": len(matches),
        "matches": matches[:50],
        "truncated": len(matches) > 50,
        "has_match": len(matches) > 0,
    }


def replace(pattern: str, replacement: str, text: str, flags: str = "") -> dict:
    """在 text 中用 pattern 匹配并替换为 replacement。"""
    flag_map = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
        "x": re.VERBOSE,
    }

    re_flags = 0
    for ch in flags:
        if ch in flag_map:
            re_flags |= flag_map[ch]
        else:
            return {"ok": False, "error": f"不支持的 flag: '{ch}'，可选: {list(flag_map.keys())}"}

    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as e:
        return {"ok": False, "error": f"正则语法错误: {e.msg} (pos {e.pos})"}

    count = 0
    def replacer(m):
        nonlocal count
        count += 1
        return m.expand(replacement)

    result_text = compiled.sub(replacer, text)

    return {
        "ok": True,
        "result": result_text[:5000],
        "replacements": count,
        "truncated": len(result_text) > 5000,
    }
