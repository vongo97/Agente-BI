"""Fase 2 de P-54: enrutar preguntas de auditoría a hechos verificados.

El LLM no calcula cifras ni las escribe. Su única tarea es seleccionar hechos
del paquete determinista y redactar un marco sin números. El servidor renderiza
las cifras exactas junto al título y la definición de cada hecho, de modo que
un número nunca puede quedar asociado a una etiqueta inventada por el modelo.
Si la selección es inválida, contiene cifras o el proveedor falla, se usa la
narrativa determinista de ``insight_auditor``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Any, Optional

from src.engine.bi_analyst import generate_ai_content

logger = logging.getLogger(__name__)

_FACT_ID_RE = re.compile(r"\b[A-Za-z]+-\d+\b")
_DIGIT_RE = re.compile(r"\d")

_EXPLICIT_INTENT_RE = re.compile(
    r"\b(auditoria|audita|auditar|audit|hallazgos?|diagnostico verificado|"
    r"perdidas? ocultas?|que esta oculto|anomalias?|outliers?)\b"
)
_QUESTION_RE = re.compile(
    r"\b(cual|cuales|que|quien|quienes|donde|por que|como|cuanto|"
    r"explica|analiza|compara|dame|muestra|resume|evolucion\w*)\b"
)
_DIMENSION_RE = re.compile(
    r"\b(region(?:es)?|segmento|segmentos|categoria|subcategoria|cliente|clientes|"
    r"ano|anios|tiempo|periodo|descuento|descuentos)\b"
)
_METRIC_RE = re.compile(
    r"\b(margen|margenes|profit|rentabilidad|perdida|perdidas|descuento|descuentos)\b"
)
_TIME_RE = re.compile(r"\b(ano|anios|tiempo|periodo|evolucion\w*|crecimiento|comportamiento)\b")


def audit_agent_enabled() -> bool:
    """Activo por defecto; ``AUDIT_AGENT_ENABLED=false`` lo desactiva."""
    return os.getenv("AUDIT_AGENT_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    # Elimina diacríticos sin depender de una librería externa.
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def is_audit_query(query: str) -> bool:
    """Detecta preguntas que la auditoría puede responder con hechos medidos.

    Es deliberadamente conservador: una pregunta genérica de ventas no se
    desvía al auditor. Las preguntas de margen, pérdida, descuento, región,
    cliente, categoría o evolución sí se enrutan cuando usan una fórmula
    interrogativa o piden una explicación.
    """
    q = _normalize(query).strip()
    if not q:
        return False
    if _EXPLICIT_INTENT_RE.search(q):
        return True

    has_question = bool(_QUESTION_RE.search(q))
    if not has_question:
        return False

    if _DIMENSION_RE.search(q) and _METRIC_RE.search(q):
        return True
    if re.search(r"\bventas?\b", q) and _TIME_RE.search(q):
        return True
    if re.search(r"\b(descuento|perdida)\b", q) and re.search(
        r"\b(cuanto|por que|explica|analiza)\b", q
    ):
        return True
    if re.search(r"\bmargen\b", q) and re.search(r"\b(por que|explica)\b", q):
        return True
    return False


def _fact_index(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(fact.get("id")): fact
        for fact in audit.get("insights", [])
        if isinstance(fact, dict) and fact.get("id")
    }


def _render_fact_line(fact: dict[str, Any]) -> str:
    return (
        f"- {fact.get('id')} | {fact.get('title')} | "
        f"valor exacto: {fact.get('display_value')} | "
        f"definición: {fact.get('definition')} | "
        f"evidencia: {fact.get('evidence')}"
    )


def _build_selection_prompt(query: str, audit: dict[str, Any]) -> str:
    facts = audit.get("insights", [])
    fact_lines = "\n".join(
        _render_fact_line(fact) for fact in facts if isinstance(fact, dict)
    )
    return (
        "Eres un analista de datos. Devuelve SOLO un objeto JSON válido, sin "
        "markdown ni texto adicional, con esta forma:\n"
        '{"intro": "texto sin cifras", "fact_ids": ["ID-01", "ID-02"], '
        '"conclusion": "texto sin cifras"}\n\n'
        f"Pregunta del usuario:\n{query}\n\n"
        "Hechos verificados (tu única fuente de verdad):\n"
        f"{fact_lines}\n\n"
        "Reglas obligatorias:\n"
        "1. Elige entre 2 y 8 IDs que respondan a la pregunta. No inventes IDs.\n"
        "2. ``intro`` y ``conclusion`` no pueden contener cifras: ni números, "
        "ni años, ni cantidades, ni monedas, ni porcentajes, ni puntos "
        "porcentuales. Escribe las cantidades con palabras si hace falta.\n"
        "3. No escribas cifras en ningún campo; el servidor insertará los "
        "valores exactos de los hechos que selecciones, junto a su título y "
        "definición.\n"
        "4. No nombres regiones, clientes, categorías, productos ni años "
        "concretos en ``intro`` o ``conclusion``; los hechos seleccionados ya "
        "contienen esos nombres. Así evitas atribuir un nombre al hecho "
        "equivocado.\n"
        "5. No afirmes causalidad ni relaciones que no estén en la definición "
        "o evidencia. Describe lo que los hechos permiten sostener.\n"
        "6. Si la pregunta no se puede responder con estos hechos, dilo en "
        "``intro`` y selecciona los hechos más cercanos; no completes con "
        "conocimiento general.\n"
        "7. No uses listas numeradas ni markdown dentro de los textos.\n"
    )


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("La respuesta no contiene un objeto JSON")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("La respuesta JSON no es un objeto")
    return parsed


def validate_fact_selection(
    selection: dict[str, Any], audit: dict[str, Any]
) -> tuple[bool, str]:
    """Valida que la selección use IDs conocidos y textos sin cifras."""
    if not isinstance(selection, dict):
        return False, "selección inválida"

    intro = selection.get("intro", "")
    conclusion = selection.get("conclusion", "")
    fact_ids = selection.get("fact_ids")
    if not isinstance(intro, str) or not isinstance(conclusion, str):
        return False, "intro o conclusión inválidas"
    if not isinstance(fact_ids, list) or not all(isinstance(item, str) for item in fact_ids):
        return False, "fact_ids inválidos"
    if len(fact_ids) < 2 or len(fact_ids) > 8:
        return False, "se requieren entre dos y ocho hechos"
    if len(set(fact_ids)) != len(fact_ids):
        return False, "hay hechos duplicados"

    known = _fact_index(audit)
    unknown = sorted(set(fact_ids) - set(known))
    if unknown:
        return False, "hechos desconocidos: " + ", ".join(unknown)

    for label, text in (("intro", intro), ("conclusion", conclusion)):
        # Las citas [KPI-03] son válidas solo si el hecho fue seleccionado.
        cited = set(_FACT_ID_RE.findall(text))
        outside_selection = sorted(cited - set(fact_ids))
        if outside_selection:
            return False, f"cita no seleccionada en {label}: " + ", ".join(outside_selection)
        clean = _FACT_ID_RE.sub("", text)
        if _DIGIT_RE.search(clean):
            return False, f"cifra literal en {label}"
        if "$" in clean or "%" in clean or "pp" in clean.lower():
            return False, f"símbolo de cifra literal en {label}"
        if len(text) > 2500:
            return False, f"{label} demasiado larga"
    return True, ""


def render_verified_answer(
    selection: dict[str, Any], audit: dict[str, Any]
) -> str:
    """Renderiza los hechos seleccionados con sus valores, títulos y definiciones."""
    known = _fact_index(audit)
    parts: list[str] = []
    intro = str(selection.get("intro", "")).strip()
    if intro:
        parts.append(intro)

    parts.append("**Hechos verificados**")
    for fact_id in selection.get("fact_ids", []):
        fact = known.get(fact_id)
        if not fact:
            raise ValueError(f"Hecho desconocido: {fact_id}")
        title = fact.get("title") or fact_id
        display = fact.get("display_value") or "no medible"
        definition = fact.get("definition") or ""
        line = f"- **{fact_id} · {title}:** {display}"
        if definition:
            line += f" — {definition}"
        parts.append(line)

    conclusion = str(selection.get("conclusion", "")).strip()
    if conclusion:
        parts.append(conclusion)
    return "\n\n".join(parts)


def build_audit_payload(audit: dict[str, Any], narrative_mode: str = "deterministic") -> dict[str, Any]:
    return {
        "insights": audit.get("insights", []),
        "profile": audit.get("profile", {}),
        "definitions": audit.get("definitions", []),
        "methodology": audit.get("methodology", []),
        "source_name": audit.get("source_name"),
        "generated_at": audit.get("generated_at"),
        "narrative_mode": narrative_mode,
    }


def generate_audit_narrative(
    query: str,
    audit: dict[str, Any],
    api_key: Optional[str] = None,
    provider: str = "gemini",
    temperature: float = 0.2,
) -> tuple[str, str, Optional[str]]:
    """Devuelve (texto, modo, motivo_de_fallback).

    ``modo`` es ``llm`` solo si la selección pasó la validación estricta; en
    cualquier otro caso se devuelve la narrativa determinista del auditor.
    """
    deterministic = str(audit.get("analysis") or "Auditoría completada.")
    if not api_key:
        return deterministic, "deterministic", "sin_api_key"

    prompt = _build_selection_prompt(query, audit)
    try:
        raw = generate_ai_content(
            prompt,
            api_key,
            provider,
            temperature=max(0.0, min(0.3, float(temperature))),
            model_level="ANALYTICS",
            system_instruction=(
                "Eres un analista que solo selecciona hechos verificados. "
                "Devuelves JSON y no escribes cifras ni nombres concretos."
            ),
            max_tokens=900,
        )
    except Exception as exc:
        logger.warning("Planificador de auditoría falló (%s): %s", type(exc).__name__, exc)
        return deterministic, "deterministic", "error_narrador"

    if not raw or raw.lstrip().startswith("⚠️"):
        return deterministic, "deterministic", "error_proveedor"

    try:
        selection = _parse_json_object(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.info("Selección de auditoría no es JSON válido: %s", exc)
        return deterministic, "deterministic", "json_invalido"

    valid, reason = validate_fact_selection(selection, audit)
    if not valid:
        logger.info("Selección de auditoría rechazada por fact-check: %s", reason)
        return deterministic, "deterministic", reason

    try:
        rendered = render_verified_answer(selection, audit)
    except ValueError as exc:
        logger.warning("No se pudo renderizar la selección verificada: %s", exc)
        return deterministic, "deterministic", "hecho_invalido"

    return rendered, "llm", None
