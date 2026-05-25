"""
json_schema_val — JSON Schema 校验。
jsonschema 为可选依赖，未安装时返回错误提示。
"""
import json


def validate(data: str, schema: str) -> dict:
    """根据 JSON Schema 校验 JSON 数据。

    Args:
        data: JSON 字符串（待校验数据）
        schema: JSON 字符串（Schema 定义）
    """
    try:
        obj = json.loads(data)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"data JSON 解析失败: {e.msg} (pos {e.pos})"}

    try:
        schema_obj = json.loads(schema)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"schema JSON 解析失败: {e.msg} (pos {e.pos})"}

    try:
        import jsonschema
        validator = jsonschema.Draft7Validator(schema_obj)
        errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
        if errors:
            error_list = []
            for e in errors:
                path = ".".join(str(p) for p in e.absolute_path) or "(root)"
                error_list.append({"path": path, "message": e.message})
            return proposal_reply(True, f"Schema校验失败——{len(errors)}个字段不符合规范",
                                  evidence={"first_error": error_list[0], "count": len(errors)},
                                  options=["根据 errors 逐个修复 JSON", "更新 schema"],
                                  valid=False, errors=error_list, count=len(errors))
        return {"ok": True, "valid": True, "count": 0}
    except ImportError:
        return {"ok": False, "error": "jsonschema 未安装，请运行: pip install jsonschema"}
    except Exception as e:
        return {"ok": False, "error": f"Schema 校验失败: {e}"}
