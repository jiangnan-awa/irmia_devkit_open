"""
http_download — 二进制文件下载。
用 urllib 下载文件到本地，自动处理重定向、进度、覆盖确认。
"""
import urllib.request
import urllib.error
import os
import time
from pathlib import Path

from ._http_utils import validate_url, SafeRedirectHandler


def _make_opener():
    return urllib.request.build_opener(SafeRedirectHandler())
from ._file_utils import human_size

# C4: 下载沙箱根目录
_DOWNLOAD_SANDBOX = Path.home() / ".irmia" / "downloads"
_MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024  # H5: 500MB 上限


def _validate_url(url: str) -> dict | None:
    return validate_url(url)


def _resolve_path(path: str) -> Path:
    """C4: 将下载路径限制在沙箱内，防止路径遍历。"""
    sandbox = _DOWNLOAD_SANDBOX.resolve()
    # 提取用户指定的文件名，丢弃目录部分防止 ../
    safe_name = Path(path).name or "download"
    resolved = (sandbox / safe_name).resolve()
    # 二次确认：resolved 必须在 sandbox 内
    if str(resolved).startswith(str(sandbox)):
        return resolved
    # 异常情况：强制回退到沙箱根
    return sandbox / "download"


def download(url: str, path: str, overwrite: bool = False, timeout: int = 60) -> dict:
    """下载文件到本地。

    Args:
        url: 下载地址
        path: 保存路径（含文件名，路径遍历会被沙箱过滤）
        overwrite: 是否覆盖已有文件
        timeout: 超时秒数

    Returns:
        {"ok": True, "path": ..., "size": ..., "elapsed_s": ...} 或 {"ok": False, "error": ...}
    """
    # C3: SSRF 防护
    err = _validate_url(url)
    if err:
        return err

    # C4: 路径沙箱
    safe_path = _resolve_path(path)
    _DOWNLOAD_SANDBOX.mkdir(parents=True, exist_ok=True)

    if safe_path.exists() and not overwrite:
        return {"ok": False, "error": f"文件已存在: {safe_path}，设 overwrite=True 覆盖"}

    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IrmiaDevKit/1.6"})
        opener = _make_opener()
        with opener.open(req, timeout=timeout) as resp:
            size = int(resp.headers.get("Content-Length", 0))
            # H5: 下载大小上限
            if size > _MAX_DOWNLOAD_SIZE:
                return {"ok": False, "error": f"文件大小 {size//1024//1024}MB 超过上限 {_MAX_DOWNLOAD_SIZE//1024//1024}MB"}
            content_type = resp.headers.get("Content-Type", "unknown")

            downloaded = 0
            with open(safe_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    # H5: 渐进式大小检查
                    if downloaded > _MAX_DOWNLOAD_SIZE:
                        f.close()
                        safe_path.unlink(missing_ok=True)  # M5: 超限清理半完成文件
                        return {"ok": False, "error": f"实际下载大小超过上限 {_MAX_DOWNLOAD_SIZE//1024//1024}MB"}
                    f.write(chunk)

        elapsed = round(time.time() - start, 2)
        actual_size = safe_path.stat().st_size
        return {
            "ok": True,
            "path": str(safe_path),
            "size": actual_size,
            "size_human": human_size(actual_size),
            "content_type": content_type,
            "elapsed_s": elapsed,
        }
    except urllib.error.HTTPError as e:
        # M5: 下载失败清理半完成文件
        safe_path.unlink(missing_ok=True)
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "url": url}
    except urllib.error.URLError as e:
        safe_path.unlink(missing_ok=True)
        return {"ok": False, "error": f"连接失败: {e.reason}", "url": url}
    except Exception as e:
        safe_path.unlink(missing_ok=True)
        return {"ok": False, "error": str(e), "url": url}
