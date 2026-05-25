"""
http_get — 纯标准库 HTTP 客户端。
快速 GET/POST，10s 超时，返回 status + body + size。
用于取 raw GitHub 内容、API 调用等场景。
"""
import urllib.request
import urllib.error
import json
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Any

# C3: 内网 IP 段黑名单
_PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _validate_url(url: str) -> dict | None:
    """校验 URL 安全性，阻止 SSRF。返回 None 表示通过，否则返回错误 dict。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "error": f"不支持的协议: {parsed.scheme}，仅允许 http/https"}
    hostname = parsed.hostname
    if not hostname:
        return {"ok": False, "error": "URL 缺少有效主机名"}
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _PRIVATE_NETS:
            if ip in net:
                return {"ok": False, "error": f"禁止访问内网地址: {hostname}"}
    except ValueError:
        pass

    try:
        addrs = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for addr in addrs:
            ip_str = addr[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                for net in _PRIVATE_NETS:
                    if ip in net:
                        return {"ok": False, "error": f"禁止访问内网地址: {hostname} 解析到 {ip_str}"}
            except ValueError:
                pass
    except socket.gaierror:
        pass

    return None


def get(url: str, headers: dict | None = None, timeout: int = 10) -> dict:
    """HTTP GET 请求。"""
    # C3: SSRF 防护
    err = _validate_url(url)
    if err:
        return err

    try:
        req = urllib.request.Request(url, headers=headers or {})
        # 保留用户自定义 UA，仅在未设置时添加默认值
        if not headers or "User-Agent" not in headers:
            req.add_header("User-Agent", "Irmia-DevKit/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": resp.status,
                "size": len(body),
                "body": body[:5000],  # 限制返回大小
                "truncated": len(body) > 5000,
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "body": body}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def post(url: str, data: Any = None, headers: dict | None = None, timeout: int = 10) -> dict:
    """HTTP POST 请求。data 可以是 dict（自动 JSON）或 str。"""
    # C3: SSRF 防护
    err = _validate_url(url)
    if err:
        return err

    try:
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            hdrs = {"Content-Type": "application/json"}
            if headers:
                hdrs.update(headers)
            headers = hdrs
        elif isinstance(data, str):
            data = data.encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers or {})
        if not headers or "User-Agent" not in headers:
            req.add_header("User-Agent", "Irmia-DevKit/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": resp.status,
                "size": len(body),
                "body": body[:5000],
                "truncated": len(body) > 5000,
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "body": body}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
