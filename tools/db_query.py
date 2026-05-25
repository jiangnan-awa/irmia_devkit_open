"""
db_query — SQLite 只读查询。
参数化防注入，仅允许 SELECT/PRAGMA，只读模式打开。
"""
import sqlite3
from pathlib import Path


def query(db_path: str, sql: str, params: list = None) -> dict:
    """只读查询 SQLite 数据库，不修改数据。

    Args:
        db_path: SQLite 数据库文件路径
        sql: SELECT 或 PRAGMA 查询语句
        params: 查询参数列表，如 [42, "active"]
    """
    p = Path(db_path)
    if not p.exists():
        return {"ok": False, "error": f"数据库不存在: {db_path}"}

    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("PRAGMA"):
        return {"ok": False, "error": "仅允许 SELECT 和 PRAGMA 语句（只读查询）"}

    params = params or []
    try:
        conn = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {
            "ok": True,
            "columns": columns,
            "rows": rows[:200],
            "count": len(rows),
            "truncated": len(rows) > 200,
        }
    except sqlite3.Error as e:
        return {"ok": False, "error": f"SQLite 错误: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
