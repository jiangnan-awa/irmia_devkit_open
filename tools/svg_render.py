"""
svg_render — SVG→PNG 渲染。
cairosvg 为可选依赖，未安装时返回错误提示。
"""
from pathlib import Path


def render(svg_path: str, output_path: str = "", width: int = 0, height: int = 0) -> dict:
    """将 SVG 文件渲染为 PNG。

    Args:
        svg_path: SVG 文件路径
        output_path: 输出 PNG 路径，默认与 SVG 同名
        width: 输出宽度（像素），0=按 SVG 原始比例
        height: 输出高度（像素），0=按 SVG 原始比例
    """
    p = Path(svg_path)
    if not p.exists():
        return {"ok": False, "error": f"SVG 文件不存在: {svg_path}"}
    if p.suffix.lower() != ".svg":
        return {"ok": False, "error": f"不是 SVG 文件: {svg_path}"}

    out = Path(output_path) if output_path else p.with_suffix(".png")

    try:
        import cairosvg
        svg_data = p.read_bytes()
        kwargs = {}
        if width:
            kwargs["output_width"] = width
        if height:
            kwargs["output_height"] = height
        cairosvg.svg2png(bytestring=svg_data, write_to=str(out), **kwargs)
        return {
            "ok": True,
            "input": svg_path,
            "output": str(out),
            "size": out.stat().st_size,
        }
    except ImportError:
        return {"ok": False, "error": "cairosvg 未安装，请运行: pip install cairosvg"}
    except Exception as e:
        return {"ok": False, "error": f"SVG 渲染失败: {e}"}
