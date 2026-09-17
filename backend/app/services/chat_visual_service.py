"""Decide whether a lesson-chat reply should come with an interactive visual — grounded only in the lesson's own content."""

import json
import logging
import re

from app.core.config import get_settings
from app.services.ai_service import generate_llm_json

logger = logging.getLogger(__name__)
settings = get_settings()

SIMULATION_CATALOG = {
    "pendulum": {
        "min_length_m": 0.2,
        "max_length_m": 2.0,
        "default_length_m": 1.0,
    },
    "concept_diagram": {
        "layouts": ("radial", "sequence"),
        "min_nodes": 2,
        "max_nodes": 8,
    },
    "math_algorithm": {
        "algorithms": ("gcd",),
        "min_value": 1,
        "max_value": 100000,
        "default_a": 48,
        "default_b": 18,
    },
}

SYSTEM_PROMPT = (
    "أنت تقرر فقط إن كان سؤال الطالب وجواب المعلّم يستفيدان من عنصر تفاعلي مرئي، "
    "وتبني محتوى هذا العنصر حصرياً من نص الدرس المرفق. "
    "أعد JSON فقط — بدون أي نص خارج JSON."
)


def _build_prompt(question: str, reply_text: str, context_chunks: str) -> str:
    context = (context_chunks or "").strip()[:6000]
    return f"""
نص الدرس (المصدر الوحيد المسموح لأي تسمية أو وصف أو رقم):
\"\"\"
{context}
\"\"\"

سؤال الطالب: "{question}"
جواب المعلّم: "{reply_text}"

اختر واحداً فقط من أربع حالات:

1) محاكاة نواس (pendulum) — فقط إذا كان السؤال عن حركة النواس أو التذبذب أو طول الخيط وتأثيره على الحركة.
أعد: {{"warranted": true, "type": "pendulum", "caption": "وصف قصير بالعربية", "length_m": 1.0}}

2) رسم تفاعلي (concept_diagram) — فقط إذا ذكر نص الدرس أعلاه أجزاءً أو خطوات أو عناصر منفصلة بأسمائها بوضوح (مثل أجزاء جهاز، خطوات عملية، محطات زمنية)، وكان عرضها بشكل مرئي يفيد فهم السؤال.
استخدم layout="radial" لأجزاء كيان واحد (جهاز، خلية، شكل) بلا ترتيب زمني.
استخدم layout="sequence" لخطوات أو مراحل أو أحداث مرتبة.
كل عنصر (node) يجب أن يكون اسمه ووصفه مأخوذين حرفياً من نص الدرس أعلاه فقط — لا تضف أي جزء أو خطوة أو تاريخ غير مذكور في النص.
أعد: {{"warranted": true, "type": "concept_diagram", "title": "عنوان قصير", "layout": "radial", "nodes": [{{"label": "اسم العنصر من نص الدرس", "description": "وصف قصير من نص الدرس", "date": "اختياري للتسلسل الزمني فقط"}}]}}

3) خوارزمية رياضية تفاعلية (math_algorithm) — فقط إذا كان نص الدرس أعلاه يشرح تحديداً خوارزمية القاسم المشترك الأكبر (GCD) بطريقة القسمة المتكررة (خوارزمية أقليدس) — وليس مجرد ذكر المصطلح عرضاً.
استخرج الرقمين من المثال الذي يستخدمه نص الدرس فعلياً إن وُجد؛ إن لم يحتوِ نص الدرس على مثال محدد بالأرقام، استخدم 48 و18 كقيمتين توضيحيتين عامتين فقط (وليس بصفتهما حقيقة من الدرس).
أعد: {{"warranted": true, "type": "math_algorithm", "algorithm": "gcd", "title": "عنوان قصير", "a": 48, "b": 18}}

4) لا حاجة لعنصر مرئي — إذا لم ينطبق ما سبق، أو إذا كان نص الدرس لا يحتوي تفاصيل كافية ومسمّاة بوضوح لبناء رسم مفيد.
أعد: {{"warranted": false}}

لا تستخدم أي معلومة عامة من خارج نص الدرس المرفق أعلاه تحت أي ظرف.
""".strip()


def _extract_visual_json(text: str) -> dict | None:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    candidates = [cleaned]
    object_match = re.search(r"\{[\s\S]*\}", cleaned)
    if object_match:
        candidates.append(object_match.group())

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, dict):
            return data
    return None


def _normalize_pendulum(data: dict, bounds: dict) -> dict | None:
    caption = str(data.get("caption") or "").strip()
    if not caption:
        return None

    try:
        length_m = float(data.get("length_m", bounds["default_length_m"]))
    except (TypeError, ValueError):
        length_m = bounds["default_length_m"]
    length_m = max(bounds["min_length_m"], min(bounds["max_length_m"], length_m))

    return {"type": "pendulum", "caption": caption, "length_m": length_m}


def _normalize_concept_diagram(data: dict, bounds: dict) -> dict | None:
    title = str(data.get("title") or "").strip()[:80]
    if not title:
        return None

    layout = data.get("layout")
    if layout not in bounds["layouts"]:
        layout = "sequence"

    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list):
        return None

    nodes = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        label = str(raw_node.get("label") or "").strip()[:60]
        if not label:
            continue
        description = str(raw_node.get("description") or "").strip()[:200]
        node = {"label": label, "description": description}
        date = raw_node.get("date")
        if date:
            node["date"] = str(date).strip()[:40]
        nodes.append(node)
        if len(nodes) >= bounds["max_nodes"]:
            break

    if len(nodes) < bounds["min_nodes"]:
        return None

    return {"type": "concept_diagram", "title": title, "layout": layout, "nodes": nodes}


def _normalize_math_algorithm(data: dict, bounds: dict) -> dict | None:
    algorithm = data.get("algorithm")
    if algorithm not in bounds["algorithms"]:
        return None

    title = str(data.get("title") or "").strip()[:80]
    if not title:
        return None

    def _clamp_int(value, default):
        try:
            parsed = abs(int(value))
        except (TypeError, ValueError):
            parsed = default
        return max(bounds["min_value"], min(bounds["max_value"], parsed)) or 1

    a = _clamp_int(data.get("a"), bounds["default_a"])
    b = _clamp_int(data.get("b"), bounds["default_b"])

    return {"type": "math_algorithm", "algorithm": algorithm, "title": title, "a": a, "b": b}


def _normalize_visual(data: dict) -> dict | None:
    if not data.get("warranted"):
        return None

    sim_type = data.get("type")
    bounds = SIMULATION_CATALOG.get(sim_type)
    if not bounds:
        return None

    if sim_type == "pendulum":
        return _normalize_pendulum(data, bounds)
    if sim_type == "concept_diagram":
        return _normalize_concept_diagram(data, bounds)
    if sim_type == "math_algorithm":
        return _normalize_math_algorithm(data, bounds)
    return None


async def decide_chat_visual(question: str, reply_text: str, context_chunks: str = "") -> dict | None:
    try:
        prompt = _build_prompt(question, reply_text, context_chunks)
        raw_text = await generate_llm_json(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=1024,
        )
        if not raw_text:
            return None

        data = _extract_visual_json(raw_text)
        if not data:
            return None

        return _normalize_visual(data)
    except Exception as exc:
        logger.warning("Chat visual decision failed: %s", exc)
        return None
