"""
html_extract — HTML 内容提取。
用 BeautifulSoup + lxml 从 HTML 中提取文本、链接、表格。
"""
from bs4 import BeautifulSoup


def extract(html: str, what: str = "text", selector: str = "") -> dict:
    """从 HTML 提取结构化内容。

    Args:
        html: HTML 字符串
        what:  提取类型
               text   — 纯文本（去标签，保留段落结构）
               links  — 所有链接 [{text, href}]
               tables — 所有表格 [{headers, rows}]
               query  — CSS 选择器结果（需 selector）
        selector: CSS 选择器，如 "div.content p"、"#main"

    Returns:
        {"ok": True, "data": ...} 或 {"ok": False, "error": ...}
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            return {"ok": False, "error": f"HTML 解析器初始化失败: {e}"}

    try:
        if what == "text":
            # 移除 script/style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # 合并多余空行
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            return {"ok": True, "data": {"text": "\n".join(lines), "line_count": len(lines)}}

        elif what == "links":
            links = []
            for a in soup.find_all("a", href=True):
                links.append({
                    "text": a.get_text(strip=True)[:100],
                    "href": a["href"],
                })
            return {"ok": True, "data": {"links": links, "count": len(links)}}

        elif what == "tables":
            tables = []
            for t in soup.find_all("table"):
                headers = [th.get_text(strip=True) for th in t.find_all("th")]
                rows = []
                for tr in t.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cols:
                        rows.append(cols)
                tables.append({"headers": headers, "rows": rows, "row_count": len(rows)})
            return {"ok": True, "data": {"tables": tables, "count": len(tables)}}

        elif what == "query":
            if not selector:
                return {"ok": False, "error": "what='query' 需要 selector 参数"}
            elements = soup.select(selector)
            results = [el.get_text(strip=True)[:200] for el in elements]
            html_snippets = []
            for el in elements[:5]:
                pretty = el.prettify()
                first_line = pretty.split("\n")[0] if "\n" in pretty else pretty[:300]
                html_snippets.append(first_line[:300])
            return {"ok": True, "data": {
                "selector": selector,
                "results": results,
                "count": len(elements),
                "html_preview": html_snippets,
            }}

        else:
            return {"ok": False, "error": f"未知提取类型: {what}，可选 text/links/tables/query"}

    except Exception as e:
        return {"ok": False, "error": f"HTML 解析失败: {e}"}
