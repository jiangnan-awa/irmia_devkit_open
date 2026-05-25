"""
csv_utils — CSV/TSV 解析与生成。
纯 csv 标准库，自动检测分隔符，返回结构化数据。
"""
import csv
import io


def parse(text: str, delimiter: str = "auto", has_header: bool = True) -> dict:
    """
    解析 CSV/TSV 文本为结构化数据。

    Args:
        text: CSV 文本
        delimiter: 分隔符，'auto' 自动检测（, 或 \\t），也可手动指定
        has_header: 首行是否为表头
    """
    if delimiter == "auto":
        # 检测：第一行 tab 多则 TSV，否则 CSV
        first_line = text.split("\n")[0] if text else ""
        delimiter = "\t" if first_line.count("\t") > first_line.count(",") else ","

    try:
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
    except Exception as e:
        return {"ok": False, "error": f"CSV 解析失败: {e}"}

    if not rows:
        return {"ok": True, "delimiter": delimiter, "headers": [], "rows": [], "count": 0}

    headers = []
    data_start = 0
    if has_header and len(rows) > 0:
        headers = [h.strip() for h in rows[0]]
        data_start = 1

    data_rows = []
    for r in rows[data_start:]:
        row_data = {}
        for i, val in enumerate(r):
            key = headers[i] if i < len(headers) else f"col_{i}"
            row_data[key] = val.strip()
        data_rows.append(row_data)

    return {
        "ok": True,
        "delimiter": "tab" if delimiter == "\t" else "comma",
        "headers": headers,
        "rows": data_rows[:200],
        "count": len(data_rows),
        "truncated": len(data_rows) > 200,
    }


def generate(rows: list[dict], delimiter: str = ",") -> dict:
    """
    将 dict 列表生成为 CSV 文本。

    Args:
        rows: [{"name": "a", "age": "1"}, ...]
        delimiter: 分隔符，默认逗号
    """
    if not rows:
        return {"ok": False, "error": "rows 为空"}

    headers = list(rows[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    return {
        "ok": True,
        "result": output.getvalue(),
        "delimiter": "tab" if delimiter == "\t" else "comma",
        "headers": headers,
        "row_count": len(rows),
    }
