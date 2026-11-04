"""Regresión P-71 (evolución de la Fase 2 de P-54): relato natural verificado.

El contrato es: el LLM escribe la interpretación en lenguaje natural y puede
usar las cifras exactas de los hechos (o derivar una variación de dos cifras
del mismo enunciado), pero cualquier cifra que no esté respaldada por el
paquete determinista hace que se use esa narrativa determinista. El cálculo
nunca lo hace el modelo.
"""
import json
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.audit_agent import (
    audit_agent_enabled,
    build_audit_payload,
    generate_audit_narrative,
    is_audit_query,
    validate_natural_narration,
)
from src.engine.insight_auditor import build_audit


def _audit() -> dict:
    rows = []
    plan = [
        (0.0, 10, 100.0, 10.0),
        (0.2, 10, 100.0, 5.0),
        (0.4, 10, 100.0, -20.0),
        (0.6, 10, 100.0, -30.0),
    ]
    order = 0
    for discount, count, sales, profit in plan:
        for index in range(count):
            order += 1
            rows.append(
                {
                    "order_id": f"O{order:03d}",
                    "order_date": f"2023-01-{index + 1:02d}",
                    "region": "North" if index % 2 else "South",
                    "category": "Tech" if discount < 0.4 else "Furniture",
                    "subcategory": "Phones" if discount < 0.4 else "Tables",
                    "customer": "Ana" if index % 2 else "Bob",
                    "sales": sales,
                    "profit": profit,
                    "discount": discount,
                }
            )
    return build_audit(pd.DataFrame(rows), source_name="test.csv")


def _fact(audit: dict, fact_id: str) -> dict:
    return next(item for item in audit["insights"] if item["id"] == fact_id)


def _payload(narration: str, fact_ids: list[str] | None = None) -> dict:
    return {
        "narration": narration,
        "fact_ids": fact_ids or ["KPI-03", "DISC-04"],
    }


class TestFeatureFlag:
    def test_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUDIT_AGENT_ENABLED", None)
            assert audit_agent_enabled()

    def test_can_be_disabled_explicitly(self):
        with patch.dict(os.environ, {"AUDIT_AGENT_ENABLED": "false"}):
            assert not audit_agent_enabled()


class TestAuditIntent:
    def test_explicit_audit_words_route_to_audit(self):
        assert is_audit_query("Haz una auditoría de los márgenes")
        assert is_audit_query("Audita los descuentos")
        assert is_audit_query("Dame los hallazgos verificados")
        assert is_audit_query("Detectar anomalías")

    def test_fact_questions_route_to_audit(self):
        assert is_audit_query("¿Qué región tiene peor margen?")
        assert is_audit_query("¿Cuáles son los clientes con más pérdidas?")
        assert is_audit_query("¿Por qué cayó el margen?")
        assert is_audit_query("¿Cuánto perdemos por descuentos?")

    def test_regular_analysis_is_not_hijacked(self):
        # P-54 (evolución 2026-10-28): las preguntas factuales sobre los datos
        # SÍ se enrutan a auditoría (el determinista es la única fuente de
        # cifras). Lo que no se desvía son las peticiones de artefactos.
        assert not is_audit_query("Genera un gráfico de ventas por región")
        assert not is_audit_query("Hola")

    def test_general_fact_questions_route_to_audit(self):
        """P-54: preguntas factuales de datos usan hechos medidos, no LLM libre."""
        assert is_audit_query("¿Cuál es el producto más vendido?")
        assert is_audit_query("Analiza estos datos")
        assert is_audit_query("Dame un resumen del dataset")
        assert is_audit_query("Compara las regiones")
        assert is_audit_query("¿Qué métricas hay en los registros?")

    def test_artifact_requests_stay_in_generative_engine(self):
        """P-54: gráficos, código, SQL y simulación no son preguntas de auditoría."""
        assert not is_audit_query("Genera un diagrama de ventas")
        assert not is_audit_query("Escribe el código Python del análisis")
        assert not is_audit_query("Genera el SQL para las ventas")
        assert not is_audit_query("Crea una simulación de escenarios")
        assert not is_audit_query("Exporta los hallazgos a PDF")


class TestNaturalNarrationValidation:
    def test_numbers_from_facts_are_accepted(self):
        audit = _audit()
        payload = _payload(
            "El margen agregado es **-8.8%** y el tramo profundo de descuento "
            "concentra el **50.0%** de las ventas.",
        )

        valid, reason = validate_natural_narration(payload, audit)
        assert valid, reason

    def test_invented_number_is_rejected(self):
        audit = _audit()
        payload = _payload("El margen agregado es **12.5%** y el resto está sano.")

        valid, reason = validate_natural_narration(payload, audit)
        assert not valid
        assert "cifra no verificada" in reason

    def test_percentage_derived_from_two_numbers_in_same_sentence_is_accepted(self):
        """El analista puede cerrar con una variación calculada de dos hechos."""
        audit = _audit()
        payload = _payload(
            "El profit pasó de **100** a **-450**: una caída del **550%**.",
            fact_ids=["DISC-01", "DISC-02"],
        )

        valid, reason = validate_natural_narration(payload, audit)
        assert valid, reason

    def test_derived_number_outside_its_sentence_is_rejected(self):
        """La derivación solo vale con las cifras que el analista tiene delante."""
        audit = _audit()
        payload = _payload(
            "El profit neto es **-350**. En otro orden de ideas, la caída fue del **550%**.",
        )

        valid, reason = validate_natural_narration(payload, audit)
        assert not valid
        assert "cifra no verificada" in reason

    def test_citation_outside_selection_is_rejected(self):
        audit = _audit()
        payload = _payload("El detalle está en KPI-01.", fact_ids=["KPI-03", "DISC-04"])

        valid, reason = validate_natural_narration(payload, audit)
        assert not valid
        assert "cita no respaldada" in reason

    def test_unknown_fact_is_rejected(self):
        audit = _audit()
        payload = _payload("Resumen del margen.", fact_ids=["KPI-03", "FAKE-01"])

        valid, reason = validate_natural_narration(payload, audit)
        assert not valid
        assert "desconocidos" in reason

    def test_too_few_facts_are_rejected(self):
        audit = _audit()
        payload = _payload("Resumen del margen.", fact_ids=["KPI-03"])

        valid, reason = validate_natural_narration(payload, audit)
        assert not valid
        assert "dos" in reason

    def test_empty_narration_is_rejected(self):
        audit = _audit()
        valid, reason = validate_natural_narration(_payload("   "), audit)
        assert not valid
        assert "ausente" in reason


class TestNarrativeFallback:
    def test_without_api_key_uses_deterministic_analysis(self):
        audit = _audit()
        text, mode, reason = generate_audit_narrative("¿Qué margen hay?", audit)

        assert mode == "deterministic"
        assert reason == "sin_api_key"
        assert text == audit["analysis"]

    def test_valid_natural_narration_is_returned_without_duplicating_facts(self):
        """P-71: la prosa va sola; las tarjetas verificadas ya se muestran debajo."""
        audit = _audit()
        narration = (
            "El margen agregado es **-8.8%** y el tramo profundo de descuento "
            "concentra el **50.0%** de las ventas. La pérdida se concentra en "
            "las líneas con descuento."
        )

        with patch(
            "src.engine.audit_agent.generate_ai_content",
            return_value=json.dumps(_payload(narration), ensure_ascii=False),
        ):
            text, mode, reason = generate_audit_narrative(
                "¿Qué margen hay?", audit, api_key="test-key", provider="gemini"
            )

        assert mode == "llm"
        assert reason is None
        assert text == narration
        assert "**Hechos verificados**" not in text

    def test_narration_with_invented_number_falls_back(self):
        audit = _audit()
        narration = "El margen agregado es **12.5%** y el resto está sano."

        with patch(
            "src.engine.audit_agent.generate_ai_content",
            return_value=json.dumps(_payload(narration), ensure_ascii=False),
        ):
            text, mode, reason = generate_audit_narrative(
                "¿Qué margen hay?", audit, api_key="test-key", provider="gemini"
            )

        assert mode == "deterministic"
        assert text == audit["analysis"]
        assert reason and "cifra no verificada" in reason

    def test_invalid_json_falls_back(self):
        audit = _audit()

        with patch("src.engine.audit_agent.generate_ai_content", return_value="no es json"):
            text, mode, reason = generate_audit_narrative(
                "¿Qué margen hay?", audit, api_key="test-key", provider="gemini"
            )

        assert mode == "deterministic"
        assert reason == "json_invalido"
        assert text == audit["analysis"]

    def test_provider_error_falls_back(self):
        audit = _audit()

        with patch(
            "src.engine.audit_agent.generate_ai_content",
            return_value="⚠️ Error del proveedor",
        ):
            text, mode, reason = generate_audit_narrative(
                "¿Qué margen hay?", audit, api_key="test-key", provider="gemini"
            )

        assert mode == "deterministic"
        assert reason == "error_proveedor"
        assert text == audit["analysis"]


def test_payload_records_narrative_mode():
    audit = _audit()
    payload = build_audit_payload(audit, "llm")

    assert payload["narrative_mode"] == "llm"
    assert payload["insights"] == audit["insights"]
    assert payload["profile"] == audit["profile"]
