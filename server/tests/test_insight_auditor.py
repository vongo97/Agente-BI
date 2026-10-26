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
        assert all(item["id"] != "KPI-02" for item in audit["insights"])
        assert all(item["id"] != "KPI-03" for item in audit["insights"])
        # P-63: ventas sin profit no lamenta columnas ausentes ni las lista
        # como "calidad"; no inventa profit/margen.
        assert "pero no hay una columna de profit" not in audit["analysis"]
        assert "columna de profit" not in audit["profile"]["quality"]
        assert [d["term"] for d in audit["definitions"]] == ["Línea", "Participación de ventas", "No medible"]

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


def make_gov_df() -> pd.DataFrame:
    """Dataset gubernamental tipo epidemiológico: fecha, categoría, métrica.
    Sin ventas ni profit: debe producir hechos genéricos verificables (P-59)."""
    rows = []
    regions = ["Norte", "Sur", "Occidente"]
    for month in range(1, 13):
        for day in range(1, 4):
            count = (month * day) % 7 + 1
            for i in range(count):
                rows.append(
                    {
                        "fecha_diagnostico": f"2021-{month:02d}-{day:02d}",
                        "departamento_nom": regions[(month + i) % 3],
                        "edad": 20 + ((month * 7 + i) % 60),
                        "id_de_caso": len(rows) + 1,
                    }
                )
    return pd.DataFrame(rows)


class TestGenericFactsWithoutSales:
    """P-59: sin ventas/profit la auditoría debe adaptarse a los datos,
    calcular hechos genéricos verificables y no hablar idioma retail."""

    def test_generic_facts_are_deterministic_and_verifiable(self):
        df = make_gov_df()
        audit = build_audit(df, source_name="casos.csv")
        ids = {f["id"] for f in audit["insights"]}

        assert "TIME-G01" in ids  # mes con más registros
        assert "CAT-G01" in ids   # composición
        assert "MET-G01" in ids   # promedio de edad
        assert "MET-G02" in ids   # mediana de edad

        peak = _fact(audit, "TIME-G01")
        expected_peak = (
            df["fecha_diagnostico"]
            .pipe(pd.to_datetime)
            .dt.to_period("M")
            .value_counts()
            .idxmax()
        )
        assert str(expected_peak) in peak["display_value"]

        mean_fact = _fact(audit, "MET-G01")
        assert mean_fact["value"] == pytest.approx(df["edad"].mean())
        median_fact = _fact(audit, "MET-G02")
        assert median_fact["value"] == pytest.approx(df["edad"].median())

    def test_no_retail_vocabulary_when_nothing_retail_was_calculated(self):
        audit = build_audit(make_gov_df(), source_name="casos.csv")
        terms = {d["term"] for d in audit["definitions"]}
        narrative = audit["analysis"]

        assert "Profit neto" not in terms
        assert "Pérdida bruta" not in terms
        assert "Umbral de descuento" not in terms
        assert "Profit neto" not in narrative
        assert "rentabilidad" not in narrative
        assert "métrica de negocio" in narrative  # acción neutral

    def test_metric_is_not_fabricated_from_text_labels(self):
        """'De 25 a 29 años' NO es un número: puede ser categoría de
        composición, pero jamás una métrica promediable (P-59)."""
        df = pd.DataFrame(
            {
                "fecha": ["2021-01-05", "2021-02-05", "2021-03-05", "2021-04-05"],
                "grupos_de_edad": ["De 25 a 29 años", "De 30 a 34 años", "De 25 a 29 años", "De 60 a 64 años"],
                "sexo": ["H", "M", "H", "M"],
                "total": ["13,25", "20,5", "8,0", "31,4"],
            }
        )
        audit = build_audit(df, source_name="ine.csv")
        metric_titles = [
            f["title"] for f in audit["insights"]
            if f["id"].startswith("MET-")
        ]
        for title in metric_titles:
            assert "grupos_de_edad" not in title
        # La métrica es 'total' (decimal con coma) con el valor exacto.
        mean_fact = _fact(audit, "MET-G01")
        assert "'total'" in mean_fact["title"]
        assert mean_fact["value"] == pytest.approx((13.25 + 20.5 + 8.0 + 31.4) / 4)
        # Y la composición SÍ puede usar el grupo de edad como categoría.
        composition = _fact(audit, "CAT-G01")
        assert "grupos_de_edad" in composition["title"]

    def test_numeric_codes_are_not_metrics(self):
        """Un código numérico de departamento no se promedia; la composición
        usa la columna legible ('departamento_nom')."""
        df = pd.DataFrame(
            {
                "fecha": ["2021-01-05", "2021-02-05", "2021-03-05", "2021-04-05", "2021-05-05", "2021-06-05"],
                "departamento": [5, 11, 17, 5, 11, 17],
                "departamento_nom": ["Antioquia", "Bogotá", "Valle", "Antioquia", "Bogotá", "Valle"],
            }
        )
        audit = build_audit(df, source_name="colombia.csv")
        titles = [f["title"] for f in audit["insights"]]
        assert not any("Promedio de 'departamento'" in title for title in titles)
        assert not any("Mediana de 'departamento'" in title for title in titles)
        assert not any("Composición por 'departamento'" in title for title in titles)

    def test_short_span_buckets_by_day_not_month(self):
        """P-62: con alcance menor a un mes, 'mes con más registros' es
        tautólogo (100%): la tarjeta agrupa por día y su participación
        es real, no 100%."""
        rows = ["2024-06-01"] * 5 + ["2024-06-02"] * 2 + ["2024-06-03"] * 3
        df = pd.DataFrame({"fecha": rows, "tipo": ["A", "B", "C"] * 3 + ["A"]})
        audit = build_audit(df, source_name="dias.csv")
        peak = _fact(audit, "TIME-G01")
        assert peak["title"] == "Día con más registros"
        assert "2024-06-01" in peak["display_value"]
        assert "50.0%" in peak["display_value"]
        assert "100.0%" not in peak["display_value"]
        assert "El día con más registros es" in audit["analysis"]
        assert "El periodo con más registros es" not in audit["analysis"]

    def test_single_day_span_has_no_peak_card(self):
        """P-62: un único día en todo el dataset no genera tarjeta:
        la cifra 100% no informa nada."""
        df = pd.DataFrame({
            "fecha": ["2024-06-01"] * 6,
            "tipo": ["A", "B", "C", "A", "B", "C"],
        })
        audit = build_audit(df, source_name="un_dia.csv")
        ids = {f["id"] for f in audit["insights"]}
        assert "TIME-G01" not in ids
        assert "CAT-G01" in ids

    def test_second_composition_exact_values(self):
        """P-62: CAT-G02 existe, usa la segunda categoría legible y sus
        cifras son exactas."""
        df = pd.DataFrame({
            "fecha": [f"2024-{m:02d}-10" for m in range(1, 11)],
            "region": ["Norte"] * 4 + ["Sur"] * 3 + ["Este"] * 2 + ["Oeste"] * 1,
            "estado": ["OK"] * 5 + ["KO"] * 3 + ["NA"] * 2,
        })
        audit = build_audit(df, source_name="dos_cat.csv")
        c1 = _fact(audit, "CAT-G01")
        c2 = _fact(audit, "CAT-G02")
        assert "'region'" in c1["title"]
        assert "'estado'" in c2["title"]
        assert c1["display_value"] == "Norte 40.0%, Sur 30.0%, Este 20.0%"
        assert c2["display_value"] == "OK 50.0%, KO 30.0%, NA 20.0%"
        assert c2["display_value"] in audit["analysis"]

    def test_no_second_composition_without_candidates(self):
        """P-62: si no hay una segunda categoría legible, no se emite
        CAT-G02 (cero hallazgos > hallazgo de relleno)."""
        df = pd.DataFrame({
            "fecha": ["2024-01-10", "2024-02-10", "2024-03-10", "2024-04-10"],
            "region": ["Norte", "Sur", "Este", "Oeste"],
            "constante": ["A"] * 4,
        })
        audit = build_audit(df, source_name="una_cat.csv")
        ids = {f["id"] for f in audit["insights"]}
        assert "CAT-G01" in ids
        assert "CAT-G02" not in ids

    def test_quality_does_not_list_retail_absences(self):
        """P-59 (feedback usuario): en datasets no retail, 'no se detectó
        ventas/profit/descuento' no es un problema de calidad; es ruido."""
        audit = build_audit(make_gov_df(), source_name="casos.csv")
        quality = " ".join(audit["profile"]["quality"])
        narrative = audit["analysis"]

        assert "columna de ventas" not in quality
        assert "columna de profit" not in quality
        assert "columna de descuento" not in quality
        assert "identificador de orden" not in quality
        assert "columna de ventas" not in narrative

    def test_partial_retail_quality_has_no_absence_notes(self):
        """P-63 (feedback usuario): ventas sin profit NO lista ausencias como
        "calidad"; describe problemas de calidad reales, no lo que falta."""
        df = pd.DataFrame(
            {
                "fecha": ["2021-01-05", "2021-02-05", "2021-03-05", "2021-04-05"],
                "sales": [100.0, 120.0, 90.0, 110.0],
            }
        )
        audit = build_audit(df, source_name="ventas.csv")
        quality = " ".join(audit["profile"]["quality"])
        assert "columna de profit" not in quality
        assert "columna de descuento" not in quality
        assert "identificador de orden" not in quality

    def test_retail_dataset_keeps_retail_definitions_and_facts(self):
        """Regresión: con ventas+profit no cambian los hechos ni el
        vocabulario (los tests de descuento ya cubren los valores)."""
        audit = build_audit(make_discount_df(), source_name="descuentos.csv")
        terms = {d["term"] for d in audit["definitions"]}
        assert "Profit neto" in terms
        assert "Umbral de descuento" in terms
        assert _fact(audit, "KPI-01")["id"] == "KPI-01"
        assert not any(f["id"] == "TIME-G01" for f in audit["insights"])


class TestSalesWithoutProfit:
    """P-63: rankings con Suma_Ingresos (ventas, sin profit) — la auditoría
    trabaja con lo que el archivo contiene: total + repartición verificable,
    sin frases de columnas ausentes."""

    SALES_DF = pd.DataFrame(
        {
            "Posicion": [1, 2, 3, 4, 5],
            "DEPARTAMENTO": ["ATLANTICO", "CUNDINAMARCA", "BOLIVAR", "SANTANDER", "RISARALDA"],
            "Cantidad_Empresas": [766, 964, 355, 500, 247],
            "Suma_Ingresos": [107.57, 86.85, 78.68, 45.59, 26.23],
        }
    )

    def test_breakdown_exact_values(self):
        audit = build_audit(self.SALES_DF, source_name="p1.csv")
        analysis = audit["analysis"]
        ids = {f["id"] for f in audit["insights"]}

        assert "KPI-01" in ids
        assert "CAT-V01" in ids

        breakdown = _fact(audit, "CAT-V01")
        # 344.92 total de ingresos; participación exacta por departamento.
        top3 = self.SALES_DF.sort_values("Suma_Ingresos", ascending=False).head(3)
        total = self.SALES_DF["Suma_Ingresos"].sum()
        shares = ", ".join(
            f"{row.DEPARTAMENTO} {row.Suma_Ingresos / total * 100:.1f}%"
            for row in top3.itertuples()
        )
        assert breakdown["display_value"] == shares
        assert breakdown["display_value"] in analysis

    def test_narrative_has_no_grieving_and_no_pending_definitions(self):
        audit = build_audit(self.SALES_DF, source_name="p1.csv")
        analysis = audit["analysis"]
        terms = {d["term"] for d in audit["definitions"]}

        assert "pero no hay una columna de profit" not in analysis
        assert "Profit neto" not in terms
        assert "Margen" not in terms
        assert "Línea" in terms
        assert "El dataset registra" in analysis

    def test_quality_reports_real_issues_not_absences(self):
        audit = build_audit(self.SALES_DF, source_name="p1.csv")
        quality = " ".join(audit["profile"]["quality"])
        assert "No se detectó" not in quality
        assert "identificador de orden" not in quality

    def test_single_row_dataset_keeps_total_without_breakdown(self):
        df = pd.DataFrame({"region": ["Norte"], "sales": [100.0]})
        audit = build_audit(df, source_name="una_linea.csv")
        ids = {f["id"] for f in audit["insights"]}
        assert "KPI-01" in ids
        assert "CAT-V01" not in ids



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
