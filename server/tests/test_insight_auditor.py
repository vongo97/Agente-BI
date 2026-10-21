"""
Regresión P-54: la auditoría debe calcular hechos verificables y no inventar
métricas cuando faltan columnas. Las definiciones de línea vs orden y de
pérdida bruta vs profit neto son parte del contrato.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.insight_auditor import AuditError, build_audit


def _fact(audit: dict, fact_id: str) -> dict:
    for item in audit["insights"]:
        if item["id"] == fact_id:
            return item
    raise AssertionError(f"No se generó el hecho {fact_id}: {[f['id'] for f in audit['insights']]}")


def make_discount_df(discount_as_percent: bool = False) -> pd.DataFrame:
    rows = []
    order = 0
    plan = [
        (0.0, 10, 100.0, 10.0, "Ana", "North", "Tech", "Phones"),
        (0.2, 10, 100.0, 5.0, "Ana", "South", "Tech", "Phones"),
        (0.4, 10, 100.0, -20.0, "Bob", "North", "Furniture", "Tables"),
        (0.6, 10, 100.0, -30.0, "Bob", "South", "Furniture", "Tables"),
    ]
    for discount, count, sales, profit, customer, region, category, subcategory in plan:
        for index in range(count):
            order += 1
            year = 2023 if index < 5 else 2024
            rows.append(
                {
                    "order_id": f"O{order:03d}",
                    "order_date": f"{year}-01-{index + 1:02d}",
                    "ship_date": f"{year}-01-{index + 3:02d}",
                    "region": region,
                    "category": category,
                    "subcategory": subcategory,
                    "customer": customer,
                    "sales": sales,
                    "profit": profit,
                    "discount": discount * 100 if discount_as_percent else discount,
                }
            )
    return pd.DataFrame(rows)


def make_line_vs_order_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["A", "A", "B", "B"],
            "sales": [100.0, 100.0, 100.0, 100.0],
            "profit": [50.0, -20.0, -10.0, -10.0],
            "discount": [0.0, 0.0, 0.0, 0.0],
        }
    )


class TestDiscountAudit:
    def test_threshold_and_deep_loss_are_exact(self):
        audit = build_audit(make_discount_df(), source_name="descuentos.csv")

        assert _fact(audit, "KPI-01")["value"] == pytest.approx(4000.0)
        assert _fact(audit, "KPI-02")["value"] == pytest.approx(-350.0)
        assert _fact(audit, "KPI-03")["value"] == pytest.approx(-0.0875)

        threshold = _fact(audit, "DISC-03")
        assert threshold["value"] == pytest.approx(0.4)
        assert threshold["display_value"] == "40.0%"
        assert _fact(audit, "DISC-04")["value"] == pytest.approx(-500.0)
        assert _fact(audit, "DISC-06")["value"] == pytest.approx(0.2)
        assert _fact(audit, "DISC-07")["value"] == pytest.approx(-300.0)
        assert _fact(audit, "DISC-07")["display_value"].startswith("-$300")

    def test_discount_0_100_is_normalized(self):
        audit = build_audit(make_discount_df(discount_as_percent=True), source_name="porcentaje.csv")
        assert _fact(audit, "DISC-03")["value"] == pytest.approx(0.4)
        assert "0-100" in " ".join(audit["profile"]["quality"])

    def test_last_profitable_level_is_not_assumed(self):
        audit = build_audit(make_discount_df(), source_name="descuentos.csv")
        assert _fact(audit, "DISC-06")["display_value"] == "20.0%"
        assert "No implica que sea el nivel óptimo" in _fact(audit, "DISC-06")["definition"]


class TestLineVsOrder:
    def test_negative_lines_are_not_negative_orders(self):
        audit = build_audit(make_line_vs_order_df(), source_name="lineas.csv")

        lines = _fact(audit, "LOSS-01")
        orders = _fact(audit, "LOSS-04")
        orders_with_negative_line = _fact(audit, "LOSS-06")
        assert lines["value"] == 3
        assert orders["value"] == 1
        assert orders_with_negative_line["value"] == 2
        assert orders_with_negative_line["sample_size"] == 2
        assert "distinto de contar líneas" in orders["definition"]
        assert "No es lo mismo que una orden con profit neto negativo" in orders_with_negative_line["definition"]
        assert audit["profile"]["grain"].startswith("línea")
        assert audit["profile"]["orders"] == 2

    def test_no_order_id_does_not_invent_orders(self):
        df = make_line_vs_order_df().drop(columns=["order_id"])
        audit = build_audit(df, source_name="sin_orden.csv")
        assert audit["profile"]["orders"] is None
        assert "sin identificador de orden" in audit["profile"]["grain"]
        assert all(item["id"] != "LOSS-04" for item in audit["insights"])


class TestRegionDiscountGap:
    def make_region_df(self) -> pd.DataFrame:
        rows = []
        # Norte: 10 líneas sin descuento y 20 con 40%; margen -10%.
        # Sur: 20 líneas sin descuento y 10 con 60%; margen 0%.
        # El umbral detectado es 40%, así que la brecha de descuento
        # profundo debe comparar 66.7% (Norte) contra 33.3% (Sur).
        for region, count, discount, profit in (
            ("Norte", 10, 0.0, 10.0),
            ("Norte", 20, 0.4, -20.0),
            ("Sur", 20, 0.0, 10.0),
            ("Sur", 10, 0.6, -20.0),
        ):
            for _ in range(count):
                rows.append(
                    {
                        "region": region,
                        "sales": 100.0,
                        "profit": profit,
                        "discount": discount,
                    }
                )
        return pd.DataFrame(rows)

    def test_region_discount_gap_uses_detected_threshold(self):
        audit = build_audit(self.make_region_df(), source_name="regiones.csv")

        assert _fact(audit, "DISC-03")["value"] == pytest.approx(0.4)
        reg02 = _fact(audit, "REG-02")
        assert reg02["display_value"] == "10.0 pp (Sur vs Norte)"
        reg03 = _fact(audit, "REG-03")
        assert reg03["value"] == pytest.approx(1.0 / 3.0)
        assert reg03["display_value"] == "33.3 pp (Norte vs Sur)"
        assert "≥40.0%" in reg03["title"]
        assert reg03["severity"] == "alta"
        assert "brecha de líneas con descuento profundo" in audit["analysis"].lower()


class TestHonestLimits:
    def test_without_profit_does_not_invent_margin(self):
        df = pd.DataFrame({"region": ["Norte", "Sur", "Norte", "Sur"], "sales": [100, 200, 300, 400]})
        audit = build_audit(df, source_name="sin_profit.csv")

        assert audit["profile"]["roles"]["profit"] is None
        assert any("profit" in item.lower() for item in audit["profile"]["quality"])
        assert all(item["id"] != "KPI-02" for item in audit["insights"])
        assert all(item["id"] != "KPI-03" for item in audit["insights"])
        assert "no hay una columna de profit" in audit["analysis"].lower()

    def test_profit_margin_is_not_used_as_profit(self):
        df = pd.DataFrame(
            {
                "sales": [100, 200, 300],
                "profit_margin": [0.1, 0.2, 0.3],
            }
        )
        audit = build_audit(df, source_name="margen.csv")
        assert audit["profile"]["roles"]["profit"] is None
        assert all(item["id"] != "KPI-02" for item in audit["insights"])

    def test_sql_engine_is_rejected_with_actionable_message(self):
        class FakeEngine:
            pass

        with pytest.raises(AuditError, match="SQL"):
            build_audit(FakeEngine(), source_name="sql")

    def test_empty_dataset_is_rejected(self):
        with pytest.raises(AuditError):
            build_audit(pd.DataFrame(), source_name="vacio.csv")


class TestNarrativeAndFigure:
    def test_narrative_uses_calculated_values(self):
        audit = build_audit(make_discount_df(), source_name="descuentos.csv")
        analysis = audit["analysis"]
        assert "Auditoría verificada" in analysis
        assert _fact(audit, "DISC-03")["display_value"] in analysis
        assert _fact(audit, "DISC-04")["display_value"].split(" · ")[0] in analysis
        assert "Pérdida bruta" in analysis
        assert "no es el profit neto" in analysis

    def test_figure_has_panels_without_llm(self):
        audit = build_audit(make_discount_df(), source_name="descuentos.csv")
        figure = audit["figure"]
        assert figure is not None
        assert len(figure.data) >= 3
        assert audit["generated_at"]
        assert audit["methodology"]
        assert audit["definitions"]

    def test_source_name_is_preserved(self):
        audit = build_audit(make_discount_df(), source_name="superstore.csv")
        assert audit["source_name"] == "superstore.csv"
        assert audit["profile"]["source_name"] == "superstore.csv"
