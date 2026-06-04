"""
codegraph — 代码语义索引与查询引擎。

Python ast 解析 + SQLite FTS5 存储。单文件，零强制依赖。
tree-sitter 可选（pip install tree-sitter tree-sitter-javascript 等）。
"""

from __future__ import annotations

import ast as py_ast
import fnmatch
import json
import os
import re
import sqlite3
import time
from pathlib import Path

try:
    import tree_sitter
    import tree_sitter_python as ts_py
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

_FTS_MIN_LENGTH = 2

_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".h": "cpp",
}

_DEFAULT_IGNORE = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".eggs", "build", "dist", "target", ".codegraph",
}

_EXPLORE_PATTERNS = [
    (re.compile(r"从\s+(\S+)\s+到\s+(\S+)"), "trace_closed"),
    (re.compile(r"from\s+(\S+)\s+to\s+(\S+)", re.IGNORECASE), "trace_closed"),
    (re.compile(r"(\S+)\s*→\s*(\S+)"), "trace_closed"),
    (re.compile(r"调用链|calls?\s+chain|trace|路径|怎么走|how.*call|who.*calls?", re.IGNORECASE), "trace_open"),
    (re.compile(r"定义了?|在哪|定义在|where.*(?:is|defined)|locate|find.*symbol", re.IGNORECASE), "symbol_search"),
]


class CodeGraph:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ensure_db()

    def _ensure_db(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            file TEXT NOT NULL,
            line INTEGER,
            signature TEXT,
            source TEXT,
            doc TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_sym TEXT NOT NULL,
            to_sym TEXT NOT NULL,
            kind TEXT NOT NULL,
            file TEXT,
            line INTEGER
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sym_name ON symbols(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sym_file ON symbols(file)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_from ON edges(from_sym)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_to ON edges(to_sym)")
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS sym_fts USING fts5(name, kind, file, signature, source)"
            )
        except Exception:
            pass
        conn.commit()
        self._conn = conn

    def _conn_get(self) -> sqlite3.Connection:
        if self._conn is None:
            self._ensure_db()
            self._conn = sqlite3.connect(self._db_path)
        return self._conn

    # ── index ─────────────────────────────────────────

    def index(self, project_dir: str, incremental: bool = False) -> dict:
        root = Path(project_dir).resolve()
        if not root.is_dir():
            return {"ok": False, "error": f"不是有效目录: {project_dir}"}

        start = time.time()
        conn = self._conn_get()
        conn.execute("DELETE FROM symbols")
        conn.execute("DELETE FROM edges")

        stats = {"files": 0, "symbols": 0, "edges": 0, "skipped": 0}
        mtimes: dict[str, float] = {}
        if incremental:
            row = conn.execute("SELECT value FROM meta WHERE key='mtimes'").fetchone()
            if row:
                try:
                    mtimes = json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    mtimes = {}

        for fpath in root.rglob("*"):
            if fpath.is_dir() and fpath.name in _DEFAULT_IGNORE:
                continue
            if fpath.is_file():
                suffix = fpath.suffix.lower()
                if suffix not in _LANG_MAP:
                    continue
                rp = str(fpath.relative_to(root))
                if incremental:
                    fmtime = fpath.stat().st_mtime
                    if rp in mtimes and mtimes[rp] >= fmtime:
                        continue
                    mtimes[rp] = fmtime
                try:
                    symbols, edges = _extract_file(str(fpath), suffix)
                    for s in symbols:
                        conn.execute(
                            "INSERT INTO symbols(name,kind,file,line,signature,source,doc) VALUES(?,?,?,?,?,?,?)",
                            (s["name"], s["kind"], rp, s.get("line"), s.get("signature"), s.get("source"), s.get("doc")),
                        )
                    for e in edges:
                        conn.execute(
                            "INSERT INTO edges(from_sym,to_sym,kind,file,line) VALUES(?,?,?,?,?)",
                            (e["from"], e["to"], e.get("kind", "calls"), rp, e.get("line")),
                        )
                    stats["symbols"] += len(symbols)
                    stats["edges"] += len(edges)
                    stats["files"] += 1
                except SyntaxError:
                    stats["skipped"] += 1
                except Exception:
                    stats["skipped"] += 1

        if incremental:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('mtimes',?)",
                (json.dumps(mtimes),),
            )
        conn.commit()
        try:
            conn.execute("DELETE FROM sym_fts")
            conn.execute(
                "INSERT INTO sym_fts(name, kind, file, signature, source) "
                "SELECT name, kind, file, signature, source FROM symbols"
            )
        except Exception:
            pass
        elapsed = round(time.time() - start, 2)
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("last_index", str(time.time())))
        conn.commit()

        summary = (
            f"索引完成：{stats['files']} 文件, {stats['symbols']} 符号, {stats['edges']} 调用边"
        )
        if stats["skipped"]:
            summary += f", {stats['skipped']} 文件因语法错误跳过"
        summary += f", 耗时 {elapsed}s"
        return {"ok": True, "summary": summary, "stats": stats}

    # ── explore ───────────────────────────────────────

    def explore(self, query: str, project_dir: str = ".") -> dict:
        conn = self._conn_get()
        row = conn.execute("SELECT value FROM meta WHERE key='last_index'").fetchone()
        if not row:
            return {
                "ok": False,
                "error": "no_index",
                "summary": "尚未建立语义索引。",
                "hint": f"运行 cg_index('{os.path.abspath(project_dir)}') 建索引（首次 ~30s）。",
            }

        qtype, match = _route_query(query)

        if qtype == "trace_closed" and match and match.re.groups >= 2:
            return self._trace_path(conn, match.group(1).strip(), match.group(2).strip(), project_dir)
        if qtype == "trace_open":
            return self._trace_open(conn, query, project_dir)
        if qtype == "symbol_search":
            target = query
            for kw in ("在哪", "哪里", "定义了", "定义在", "where is", "where", "find", "locate"):
                target = target.replace(kw, " ")
            target = " ".join(target.split())
            return self._search_symbol(conn, target, project_dir)
        return self._explore_fallback(conn, query, project_dir)

    def _search_symbol(self, conn, target: str, project_dir: str) -> dict:
        symbols = self._fts_search(conn, target, limit=10)
        if not symbols:
            return {
                "ok": True,
                "found": False,
                "query_type": "symbol_search",
                "summary": f"未找到符号 '{target}'。",
                "symbols": [],
                "hint": "试试 rg_search 搜索包含该关键字的文件；或用全项目自然语言搜：cg_explore('项目中如何...')",
            }
        callers = {}
        for s in symbols[:5]:
            callers[s["name"]] = [r[0] for r in conn.execute(
                "SELECT from_sym FROM edges WHERE to_sym=? LIMIT 5", (s["name"],)
            ).fetchall()]
        return {
            "ok": True,
            "found": True,
            "query_type": "symbol_search",
            "summary": f"找到 {len(symbols)} 个匹配 '{target}' 的符号。",
            "symbols": symbols[:10],
            "callers": callers,
            "hint": "需要调用链？用 cg_explore('从 X 到 Y') 精确追踪。",
        }

    def _trace_path(self, conn, from_sym: str, to_sym: str, project_dir: str) -> dict:
        path = _bfs_path(conn, from_sym, to_sym, max_depth=6)
        if path:
            return {
                "ok": True,
                "found": True,
                "query_type": "trace",
                "summary": f"从 {from_sym} 到 {to_sym} 的调用链 ({len(path)-1} 跳): {' → '.join(path)}",
                "path": path,
                "hint": "需要看具体代码？用 dir_list + file_read 查看对应文件。",
            }
        # 双向尝试
        fwd = _bfs_path(conn, from_sym, to_sym, max_depth=10)
        if fwd:
            return {
                "ok": True, "found": True, "query_type": "trace",
                "summary": f"(长路径 {len(fwd)-1} 跳) {' → '.join(fwd)}",
                "path": fwd,
            }
        return {
            "ok": True, "found": False, "query_type": "trace",
            "summary": f"从 {from_sym} 到 {to_sym} 未找到静态调用链（可能跨模块、动态调用或异步）。",
            "unresolved": [{"from": from_sym, "to": to_sym, "reason": "BFS 未找到路径"}],
            "hint": f"用 rg_search 搜索 to_sym 在哪些文件中被引用。",
        }

    def _trace_open(self, conn, query: str, project_dir: str) -> dict:
        symbols = self._fts_search(conn, query, limit=4)
        if not symbols:
            return {"ok": True, "found": False, "query_type": "trace",
                    "summary": f"未找到与 '{query}' 相关的符号。",
                    "hint": "试试更精确的函数名或符号名。"}
        sname = symbols[0]["name"]
        callers = [r[0] for r in conn.execute("SELECT from_sym FROM edges WHERE to_sym=? LIMIT 8", (sname,)).fetchall()]
        callees = [r[0] for r in conn.execute("SELECT to_sym FROM edges WHERE from_sym=? LIMIT 8", (sname,)).fetchall()]
        return {
            "ok": True, "found": True, "query_type": "trace",
            "summary": f"{sname} 的调用关系：{len(callers)} 个调用者, {len(callees)} 个被调用者。",
            "symbol": symbols[0],
            "callers": callers,
            "callees": callees,
            "hint": f"精确追踪：cg_explore('从 X → {sname}')",
        }

    def _explore_fallback(self, conn, query: str, project_dir: str) -> dict:
        symbols = self._fts_search(conn, query, limit=8)
        return {
            "ok": True, "found": len(symbols) > 0, "query_type": "explore",
            "summary": f"自然语言探索 '{query}'：找到 {len(symbols)} 个相关符号。",
            "symbols": symbols,
            "hint": "缩小范围：用符号名精确搜索，或 '从 X 到 Y' 追踪调用链。",
        }

    def _fts_search(self, conn, query: str, limit: int = 8) -> list[dict]:
        # LIKE 精确匹配优先 + FTS5 语义搜索兜底
        rows = conn.execute(
            "SELECT name, kind, file, signature, source FROM symbols WHERE name LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        if not rows:
            try:
                tokens = [t for t in re.split(r"\s+", query) if len(t) >= _FTS_MIN_LENGTH]
                if tokens:
                    fts_query = " OR ".join(tokens)
                    rows = conn.execute(
                        "SELECT name, kind, file, signature, source FROM sym_fts "
                        "WHERE sym_fts MATCH ? ORDER BY rank LIMIT ?",
                        (fts_query, limit),
                    ).fetchall()
            except Exception:
                pass
        result = []
        for r in rows:
            d = {"name": r[0], "kind": r[1], "file": r[2], "signature": r[3], "source": r[4] or ""}
            d["source"] = d["source"][:200]
            result.append(d)
        return result


def _extract_file(filepath: str, suffix: str) -> tuple[list[dict], list[dict]]:
    lang = _LANG_MAP.get(suffix, "")
    if lang == "python":
        return _extract_python(filepath)
    if HAS_TREE_SITTER and lang in ("javascript", "typescript", "go", "rust"):
        try:
            return _extract_ts(filepath, lang)
        except Exception:
            pass
    return [], []


# ── Python AST ───────────────────────────────────────

def _extract_python(filepath: str) -> tuple[list[dict], list[dict]]:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()
    tree = py_ast.parse(source)
    symbols: list[dict] = []
    edges: list[dict] = []

    class Visitor(py_ast.NodeVisitor):
        def __init__(self):
            self._scope: list[str] = []

        def _full_name(self, name: str) -> str:
            return ".".join(self._scope + [name]) if self._scope else name

        def visit_FunctionDef(self, node):
            fn = self._full_name(node.name)
            sig = _py_sig(node)
            src = py_ast.get_source_segment(source, node) or ""
            symbols.append({"name": fn, "kind": "function", "line": node.lineno,
                           "signature": sig, "source": src[:300]})
            extracted = _extract_calls(node, source, fn)
            edges.extend(extracted)
            self._scope.append(node.name)
            self.generic_visit(node)
            self._scope.pop()

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_ClassDef(self, node):
            cls = self._full_name(node.name)
            symbols.append({"name": cls, "kind": "class", "line": node.lineno,
                           "signature": f"class {node.name}", "source": ""})
            self._scope.append(node.name)
            for b in node.body:
                if isinstance(b, (py_ast.FunctionDef, py_ast.AsyncFunctionDef)):
                    fn = self._full_name(b.name)
                    sig = _py_sig(b)
                    src = py_ast.get_source_segment(source, b) or ""
                    symbols.append({"name": f"{cls}.{b.name}", "kind": "method", "line": b.lineno,
                                   "signature": sig, "source": src[:300]})
            self.generic_visit(node)
            self._scope.pop()

        def visit_Import(self, node):
            for alias in node.names:
                edges.append({"from": self._scope[-1] if self._scope else "(module)",
                             "to": alias.name, "kind": "imports", "line": node.lineno})

        def visit_ImportFrom(self, node):
            mod = node.module or ""
            for alias in node.names:
                edges.append({"from": self._scope[-1] if self._scope else "(module)",
                              "to": f"{mod}.{alias.name}" if mod else alias.name,
                              "kind": "imports", "line": node.lineno})

    Visitor().visit(tree)
    return symbols, edges


def _py_sig(node: py_ast.FunctionDef) -> str:
    args = []
    for a in node.args.args:
        arg = a.arg
        if a.annotation:
            arg += f": {py_ast.unparse(a.annotation)}"
        args.append(arg)
    prefix = "async def" if isinstance(node, py_ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


def _extract_calls(node, source: str, caller: str) -> list[dict]:
    edges: list[dict] = []
    unresolved: list[str] = []

    class CallVisitor(py_ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, py_ast.Name):
                edges.append({"from": caller, "to": node.func.id, "kind": "calls",
                             "line": getattr(node, "lineno", None)})
            elif isinstance(node.func, py_ast.Attribute):
                try:
                    parts = _unparse_attr(node.func)
                    edges.append({"from": caller, "to": ".".join(parts), "kind": "calls",
                                 "line": getattr(node, "lineno", None)})
                except Exception:
                    unresolved.append(py_ast.get_source_segment(source, node) or "?")
            elif isinstance(node.func, py_ast.Call):
                unresolved.append(py_ast.get_source_segment(source, node) or "?")
            self.generic_visit(node)

    CallVisitor().visit(node)
    for u in unresolved[:3]:
        edges.append({"from": caller, "to": f"(unresolved: {u[:60]})", "kind": "unresolved"})
    return edges


def _unparse_attr(node) -> list[str]:
    if isinstance(node, py_ast.Attribute):
        return _unparse_attr(node.value) + [node.attr]
    if isinstance(node, py_ast.Name):
        return [node.id]
    return ["?"]


# ── tree-sitter ───────────────────────────────────────

_TS_LANG_PARSERS: dict[str, "tree_sitter.Parser"] = {}

def _get_ts_parser(lang: str):
    if lang in _TS_LANG_PARSERS:
        return _TS_LANG_PARSERS[lang]
    try:
        if lang == "python":
            parser = tree_sitter.Parser(tree_sitter.Language(ts_py.language()))
        elif lang in ("javascript", "typescript"):
            import tree_sitter_javascript as ts_js
            import tree_sitter_typescript as ts_ts
            lang_mod = ts_ts if lang == "typescript" else ts_js
            parser = tree_sitter.Parser(tree_sitter.Language(lang_mod.language()))
        else:
            raise ImportError(f"no grammar for {lang}")
        _TS_LANG_PARSERS[lang] = parser
        return parser
    except Exception:
        return None


def _extract_ts(filepath: str, lang: str) -> tuple[list[dict], list[dict]]:
    parser = _get_ts_parser(lang)
    if parser is None:
        return [], []
    with open(filepath, "rb") as f:
        source = f.read()
    tree = parser.parse(source)
    symbols: list[dict] = []
    edges: list[dict] = []
    _walk_ts(tree.root_node, source, filepath, symbols, edges)
    return symbols, edges


def _walk_ts(node, source: bytes, filepath: str, symbols: list, edges: list, scope: str = ""):
    from tree_sitter import Node
    text = lambda n: source[n.start_byte:n.end_byte].decode("utf-8", errors="replace")

    if node.type == "function_declaration":
        name_node = node.child_by_field_name("name")
        name = text(name_node) if name_node else "?"
        fn = f"{scope}.{name}" if scope else name
        symbols.append({"name": fn, "kind": "function",
                       "line": node.start_point[0] + 1, "signature": text(node).split("\n")[0][:120]})

    elif node.type == "class_declaration":
        name_node = node.child_by_field_name("name")
        name = text(name_node) if name_node else "?"
        cls = f"{scope}.{name}" if scope else name
        symbols.append({"name": cls, "kind": "class", "line": node.start_point[0] + 1,
                       "signature": text(node).split("\n")[0][:120]})
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                _walk_ts(child, source, filepath, symbols, edges, cls)

    elif node.type == "call_expression":
        fn_node = node.child_by_field_name("function")
        if fn_node:
            called = text(fn_node)
            if scope and called:
                edges.append({"from": scope, "to": called, "kind": "calls",
                             "line": node.start_point[0] + 1})

    for child in node.children:
        _walk_ts(child, source, filepath, symbols, edges, scope)


# ── BFS ───────────────────────────────────────────────

def _bfs_path(conn, start: str, end: str, max_depth: int = 6) -> list[str] | None:
    from collections import deque
    q = deque()
    q.append((start, [start], {start}))
    while q:
        node, path, visited = q.popleft()
        if len(path) > max_depth:
            continue
        rows = conn.execute("SELECT to_sym FROM edges WHERE from_sym=? AND kind='calls'", (node,)).fetchall()
        for (nxt,) in rows:
            if nxt == end:
                return path + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                q.append((nxt, path + [nxt], visited))
    return None


def _route_query(query: str) -> tuple[str, re.Match | None]:
    for pattern, qtype in _EXPLORE_PATTERNS:
        m = pattern.search(query)
        if m:
            return qtype, m
    return "explore", None
