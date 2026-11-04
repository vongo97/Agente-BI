"""Fase 2 de P-54, evolucionada en P-71: auditoría con relato natural verificado.

El LLM ya no se limita a seleccionar tarjetas: escribe la lectura del dataset
en lenguaje natural, con comparaciones y cautelas. Para que no pueda inventar,
cada cifra de su prosa se verifica contra el paquete determinista: debe existir
literalmente en los hechos (o derivarse de dos cifras del mismo enunciado, como
una variación porcentual). Una sola cifra no verificada, un ID desconocido o un
proveedor caído hacen que se use la narrativa determinista de
``insight_auditor``. El cálculo siempre es pandas; el LLM solo interpreta.
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
# Cifras con separadores de miles/decimales: 44.584 · 27,3 · 1,234.56
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")

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
_GENERAL_DATA_INTENT_RE = re.compile(
    r"\b(analiza\w*|resumen|resume|compara\w*|describe\w*|muestra|destaca\w*|"
    r"hallazgos?|insights?|conclusiones?)\b"
)
_DATA_CONTEXT_RE = re.compile(
    r"\b(datos?|documentos?|archivos?|dataset|tabla|ventas?|ingresos?|profit|"
    r"margenes?|perdidas?|descuentos?|regiones?|productos?|clientes?|registros?|"
    r"casos?|metricas?|resultados?)\b"
)
_NON_AUDIT_ACTION_RE = re.compile(
    r"\b(grafico|grafica|plot|visualizacion|diagrama|codigo|script|sql|"
    r"simulacion|escenario|exporta|descarga|genera\s+(?:un\s+)?(?:grafico|grafica|diagrama))\b"
)


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
    # P-54: las peticiones de artefactos (gráfico, código, SQL, simulación,
    # exportación) no son preguntas de auditoría, aunque mencionen hallazgos
    # o datos. Se comprueba antes que la intención explícita para que
    # "exporta los hallazgos" no se desvíe al auditor.
    if _NON_AUDIT_ACTION_RE.search(q):
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
    # P-54: las preguntas analíticas comunes también usan hechos medidos como
    # fuente única de cifras. Peticiones de gráficos/código siguen en el motor
    # generativo, y el saludo/ayuda general no se desvía al auditor.
    if _GENERAL_DATA_INTENT_RE.search(q):
        return True
    if has_question and _DATA_CONTEXT_RE.search(q):
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


def _dataset_context(audit: dict[str, Any]) -> str:
    profile = audit.get("profile") or {}
    quality = profile.get("quality") or []
    quality_text = " ".join(str(item) for item in quality) if quality else "sin notas"
    date_range = ""
    if profile.get("date_start") and profile.get("date_end"):
        date_range = f" · {profile.get('date_start')} → {profile.get('date_end')}"
    return (
        f"Archivo: {audit.get('source_name')}\n"
        f"Filas: {profile.get('rows')} · Columnas: {profile.get('columns')}"
        f"{date_range}\n"
        f"Calidad: {quality_text}"
    )


def _build_narrative_prompt(query: str, audit: dict[str, Any]) -> str:
    facts = [
        fact for fact in audit.get("insights", []) if isinstance(fact, dict)
    ]
    fact_lines = "\n".join(_render_fact_line(fact) for fact in facts)
    return (
        "Eres un analista de datos senior. Tu tarea es EXPLICAR el dataset a un "
        "cliente no técnico, como lo haría un analista en una reunión: qué "
        "patrón se ve, qué significa, qué número importa y qué cautela hay que "
        "tener. Devuelve SOLO un objeto JSON válido, sin markdown de bloque:\n"
        '{"narration": "texto en español", "fact_ids": ["ID-01", "ID-02"]}\n\n'
        f"Pregunta del usuario:\n{query}\n\n"
        f"Contexto del dataset:\n{_dataset_context(audit)}\n\n"
        "Hechos verificados (tu única fuente de verdad):\n"
        f"{fact_lines}\n\n"
        "Reglas obligatorias:\n"
        "1. Escribe 2 a 4 párrafos de prosa natural, en español neutro, sin "
        "títulos, sin listas y sin tablas. Puedes usar **negritas** para las "
        "cifras clave.\n"
        "2. Empieza por lo que importa para el cliente, no por el archivo ni "
        "por la metodología. Nada de frases de relleno del tipo 'el análisis "
        "permite identificar patrones'.\n"
        "3. Usa SOLO las cifras que aparecen literalmente en los hechos, tal "
        "como están escritas. No calcules cifras nuevas, no redondees, no "
        "conviertas unidades ni inventes proporciones.\n"
        "4. Puedes comparar magnitudes entre hechos y señalar cautelas "
        "(años incompletos, cobertura desigual, pocos datos), pero no afirmes "
        "causalidad ni relaciones que los hechos no sostengan.\n"
        "5. Prohibido el conocimiento externo: no cites población, historia, "
        "contexto del país ni nada que no esté en los hechos.\n"
        "6. Nombra entidades (departamentos, categorías, productos) solo si "
        "aparecen en los hechos, y únelas siempre a la cifra del mismo hecho.\n"
        "7. Si los hechos no responden la pregunta, dilo en la primera frase "
        "y explica qué sí permiten ver. No rellenes con generalidades.\n"
        "8. ``fact_ids``: entre 2 y 8 IDs de los hechos que usaste. No "
        "inventes IDs ni cites IDs dentro de la narración.\n"
        "9. Máximo 1800 caracteres en ``narration``.\n"
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


def _number_candidates(token: str) -> set[float]:
    """Interpretaciones razonables de una cifra escrita.

    ``44.584`` puede ser cuarenta y cuatro mil quinientos ochenta y cuatro
    (separador de miles) o 44.584 (decimal). Se aceptan ambas: lo importante
    es que los dígitos existan en el paquete verificado.
    """
    values: set[float] = set()
    cleaned = (token or "").strip()
    if not cleaned:
        return values
    digits = re.sub(r"[.,]", "", cleaned)
    try:
        values.add(round(float(digits), 4))
    except ValueError:
        return values
    if "." in cleaned or "," in cleaned:
        normalized = cleaned.replace(",", ".")
        head, _, tail = normalized.rpartition(".")
        if head and tail:
            try:
                values.add(round(float(head.replace(".", "") + "." + tail), 4))
            except ValueError:
                pass
    return values


def _allowed_numbers(audit: dict[str, Any]) -> set[float]:
    """Todas las cifras que el paquete determinista contiene, en cualquier campo."""
    allowed: set[float] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                visit(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                visit(value)
        elif isinstance(node, bool):
            return
        elif isinstance(node, (int, float)):
            # Se acepta el valor y su magnitud: la prosa escribe "perdió 8.8%"
            # aunque el hecho guarde -8.8. El signo va en las palabras.
            allowed.add(round(float(node), 4))
            allowed.add(round(abs(float(node)), 4))
        elif isinstance(node, str):
            for token in _NUMBER_RE.findall(node):
                allowed.update(_number_candidates(token))

    visit(audit)
    return allowed


def _sentence_numbers(narration: str) -> list[list[tuple[str, set[float]]]]:
    """Cifras por enunciado, ignorando los IDs de hecho (KPI-03)."""
    clean = _FACT_ID_RE.sub(" ", narration)
    sentences = re.split(r"(?<=[.!?\n])\s+", clean)
    return [
        [(token, _number_candidates(token)) for token in _NUMBER_RE.findall(sentence)]
        for sentence in sentences
        if sentence.strip()
    ]


def _derivable_from_sentence(
    claim_candidates: set[float], other_values: list[float]
) -> bool:
    """Acepta una cifra derivada de dos cifras del mismo enunciado.

    Cubre el caso legítimo "de 44.584 en 2020 a 5.397 en 2021, una caída del
    88%": el porcentaje no está en los hechos, pero sale de dos cifras que sí
    están y que el analista tiene delante en la misma frase.
    """
    magnitudes = {round(abs(value), 4) for value in claim_candidates}
    # El signo va en las palabras ("cayó de 100 a 450"): se prueban ambas
    # variantes para no perder una caída real por el guion.
    signed: list[float] = []
    for value in other_values:
        for candidate in (value, -value):
            if candidate not in signed:
                signed.append(candidate)
    for a in signed:
        if not a:
            continue
        for b in signed:
            for derived in ((b - a) / a * 100.0, b / a * 100.0):
                if any(abs(mag - abs(derived)) <= 0.5 + 0.01 * abs(derived) for mag in magnitudes):
                    return True
    return False


def validate_natural_narration(
    payload: dict[str, Any], audit: dict[str, Any]
) -> tuple[bool, str]:
    """Valida prosa natural y que cada cifra esté respaldada por la auditoría."""
    if not isinstance(payload, dict):
        return False, "respuesta inválida"

    narration = payload.get("narration")
    fact_ids = payload.get("fact_ids")
    if not isinstance(narration, str) or not narration.strip():
        return False, "narración ausente"
    if not isinstance(fact_ids, list) or not all(isinstance(item, str) for item in fact_ids):
        return False, "fact_ids inválidos"
    if len(fact_ids) < 2 or len(fact_ids) > 8:
        return False, "se requieren entre dos y ocho hechos"
    if len(set(fact_ids)) != len(fact_ids):
        return False, "hay hechos duplicados"
    if len(narration) > 2200:
        return False, "narración demasiado larga"

    known = _fact_index(audit)
    unknown = sorted(set(fact_ids) - set(known))
    if unknown:
        return False, "hechos desconocidos: " + ", ".join(unknown)

    cited = set(_FACT_ID_RE.findall(narration)) - set(fact_ids)
    if cited:
        return False, "cita no respaldada: " + ", ".join(sorted(cited))

    allowed = _allowed_numbers(audit)
    for sentence in _sentence_numbers(narration):
        for index, (token, candidates) in enumerate(sentence):
            if candidates & allowed:
                continue
            others = [
                value
                for position, (_, other) in enumerate(sentence)
                if position != index
                for value in other
            ]
            if _derivable_from_sentence(candidates, others):
                continue
            return False, f"cifra no verificada: {token}"
    return True, ""


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

    ``modo`` es ``llm`` solo si la narración pasó la verificación de cifras; en
    cualquier otro caso se devuelve la narrativa determinista del auditor.
    """
    deterministic = str(audit.get("analysis") or "Auditoría completada.")
    if not api_key:
        return deterministic, "deterministic", "sin_api_key"

    prompt = _build_narrative_prompt(query, audit)
    try:
        raw = generate_ai_content(
            prompt,
            api_key,
            provider,
            temperature=max(0.0, min(0.4, float(temperature))),
            model_level="ANALYTICS",
            system_instruction=(
                "Eres un analista de datos que explica un dataset en lenguaje "
                "natural usando SOLO las cifras verificadas que recibe. "
                "Devuelves JSON y no inventas cifras, entidades ni contexto."
            ),
            max_tokens=1100,
        )
    except Exception as exc:
        logger.warning("Narrador de auditoría falló (%s): %s", type(exc).__name__, exc)
        return deterministic, "deterministic", "error_narrador"

    if not raw or raw.lstrip().startswith("⚠️"):
        return deterministic, "deterministic", "error_proveedor"

    try:
        payload = _parse_json_object(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.info("Narración de auditoría no es JSON válido: %s", exc)
        return deterministic, "deterministic", "json_invalido"

    valid, reason = validate_natural_narration(payload, audit)
    if not valid:
        logger.info("Narración de auditoría rechazada por verificación: %s", reason)
        return deterministic, "deterministic", reason

    return str(payload["narration"]).strip(), "llm", None
