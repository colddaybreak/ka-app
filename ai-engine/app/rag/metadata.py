# ai-engine/app/rag/metadata.py
import json
import re
from app.models.llm import get_llm

MAX_TEXT_CHARS = 8000
MAX_SCHEMA_KEYS = 20


def extract_metadata(text: str, schema: list[dict]) -> dict:
    """按模板让 LLM 从文档文本中提取元数据值

    模板项格式：{"key": "department", "type": "string", "description": "所属部门"}。
    返回键值字典（null 值剔除）；无模板/无文本/解析失败时返回空字典。
    """
    if not schema or not text:
        return {}
    field_lines = []
    for i, s in enumerate(schema[:MAX_SCHEMA_KEYS], 1):
        key = (s.get("key") or s.get("name") or "").strip()
        if not key:
            continue
        desc = (s.get("description") or "").strip()
        field_lines.append(
            f"{i}. {key!r}（类型: {s.get('type', 'string')}）说明: {desc}"
        )
    if not field_lines:
        return {}

    prompt = (
        "你是文档元数据提取器。请根据文档内容，为以下字段提取元数据值。\n"
        f"字段定义：\n{chr(10).join(field_lines)}\n\n"
        "要求：\n"
        "1. 只输出一个 JSON 对象，键为字段名；number/boolean 类型不要加引号，"
        "date 类型用 YYYY-MM-DD。\n"
        "2. 文档中没有依据的字段输出 null。\n"
        "3. 不要输出 JSON 以外的任何内容。\n\n"
        f"文档内容（前 {MAX_TEXT_CHARS} 字）：\n{text[:MAX_TEXT_CHARS]}"
    )
    try:
        llm = get_llm(temperature=0)
        raw = llm.invoke(
            [{"role": "user", "content": prompt}]
        ).content
    except Exception as e:
        print(f"metadata extract failed: {e}")
        return {}

    data = _parse_json(raw)
    if not isinstance(data, dict):
        return {}
    return _coerce_values(data, schema)


def _parse_json(raw: str):
    """容错解析：json.loads → 提取首个 {...} 块；均失败返回 None"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def _coerce_values(data: dict, schema: list[dict]) -> dict:
    """按键声明类型转换值，非法值剔除（null、类型不匹配、枚举外取值）"""
    fields = {}
    for s in schema:
        key = (s.get("key") or s.get("name") or "").strip()
        if key:
            fields[key] = s
    result = {}
    for key, raw in data.items():
        if raw is None:
            continue
        s = fields.get(key)
        t = (s or {}).get("type", "string")
        value = raw
        if t == "number":
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
        elif t == "boolean":
            if isinstance(value, str):
                value = value.strip().lower() in ("true", "是", "1")
        elif t == "date":
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)):
                continue
        elif t == "enum":
            options = [str(o).strip() for o in ((s or {}).get("options") or [])]
            if options and str(value) not in options:
                continue
        result[key] = value
    return result