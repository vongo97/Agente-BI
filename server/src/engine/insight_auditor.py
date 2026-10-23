"""
Auditoría determinista de un dataset tabular.

Fase 1 de P-54: calcular hechos verificables con pandas y construir una
narrativa *solo* a partir de esos hechos. No ejecuta código generado por un
LLM y no requiere una API key. Si una métrica no se puede calcular porque
falta la columna necesaria, se dice explícitamente; no se estima.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Marca persistida en Message.analysis_code para reconocer una auditoría
# verificada. No es código ejecutable; el filtro del dashboard la trata como
# una figura estática.
AUDIT_MARKER = "__VEKTRA_AUDIT__"


class AuditError(ValueError):
    """Error de datos que se puede mostrar al usuario sin filtrar detalles internos."""


@dataclass
class AuditFact:
    id: str
    title: str
    value: float
    display_value: str
    unit: str
    category: str
    severity: str
    direction: str
    definition: str
    evidence: str
    sample_size: int


ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "sales": (
        "sales", "sale", "ventas", "venta", "revenue", "ingresos", "ingreso",
        "total_sales", "monto", "importe", "facturacion", "amount",
    ),
    "profit": (
        "profit", "ganancia", "utilidad", "beneficio", "resultado",
        "net_profit", "profit_amount",
    ),
    "discount": (
        "discount", "descuento", "dscto", "discount_rate", "descuento_pct",
        "discount_percent", "porcentaje_descuento",
    ),
    "order_id": (
        "order_id", "orderid", "order_number", "order_no", "pedido_id",
        "id_pedido", "orden_id", "invoice_id", "invoice_no", "factura_id",
        "factura", "id_orden",
    ),
    "date": (
        "order_date", "fecha_pedido", "fecha_orden", "fecha", "date",
        "created_at", "fecha_creacion", "transaction_date", "fecha_transaccion",
    ),
    "ship_date": (
        "ship_date", "fecha_envio", "fecha_entrega", "delivery_date",
        "shipping_date", "fecha_despacho", "dispatch_date",
    ),
    "customer": (
        "customer_name", "customer", "cliente", "nombre_cliente",
        "customer_id", "id_cliente", "client", "buyer",
    ),
    "category": (
        "category", "categoria", "linea", "line", "department", "departamento",
    ),
    "subcategory": (
        "subcategory", "subcategoria", "sub_category", "sublinea", "subline",
    ),
    "region": (
        "region", "region_name", "zona", "territorio", "state", "province",
        "country", "pais",
    ),
    "product": (
        "product_name", "product", "producto", "item", "sku", "article",
    ),
    "quantity": ("quantity", "qty", "cantidad", "units", "unidades"),
}

ROLE_LABELS = {
    "sales": "ventas",
    "profit": "profit",
    "discount": "descuento",
    "order_id": "orden",
    "date": "fecha de pedido",
    "ship_date": "fecha de envío",
    "customer": "cliente",
    "category": "categoría",
    "subcategory": "subcategoría",
    "region": "región",
    "product": "producto",
    "quantity": "cantidad",
}

DEFINITIONS = [
    {
        "term": "Línea",
        "definition": "Una fila del dataset. Si hay identificador de orden, una orden puede contener varias líneas.",
    },
    {
        "term": "Orden",
        "definition": "Agrupación por la columna de orden. El profit de una orden es la suma del profit de sus líneas.",
    },
    {
        "term": "Profit neto",
        "definition": "Suma de todos los profits, positivos y negativos. Es la ganancia o pérdida final del periodo.",
    },
    {
        "term": "Pérdida bruta",
        "definition": "Suma únicamente de los profits negativos. No descuenta las ganancias positivas, por eso no es el profit neto.",
    },
    {
        "term": "Margen",
        "definition": "Profit dividido entre ventas. No es el promedio de márgenes por línea.",
    },
    {
        "term": "Descuento",
        "definition": "Fracción del precio. 0.30 equivale a 30%. Los niveles se comparan por su valor exacto redondeado.",
    },
    {
        "term": "Umbral de descuento",
        "definition": "Primer nivel exacto con al menos 10 líneas cuyo profit agregado es negativo.",
    },
    {
        "term": "No medible",
        "definition": "Si falta la columna requerida, el hallazgo se omite. No se estima ni se inventa una cifra.",
    },
]

# Definiciones mostradas cuando no se calculó nada de retail (sin ventas ni
# profit). El vocabulario de margen/descuento no aplica y solo confunde a
# datasets gubernamentales, científicos u operativos (P-59).
GENERIC_DEFINITIONS = [
    {
        "term": "Línea",
        "definition": "Una fila del dataset. Sin identificador de transacción, cada fila es una observación independiente.",
    },
    {
        "term": "Periodo pico",
        "definition": "Año-mes con mayor número de registros. La participación se calcula sobre el total de fechas válidas.",
    },
    {
        "term": "Composición",
        "definition": "Top 3 valores de una columna categórica, ordenados por número de registros. El porcentaje es su participación sobre el total.",
    },
    {
        "term": "Promedio y mediana",
        "definition": "Estadísticos de la columna métrica indicada, calculados solo con valores numéricos no vacíos.",
    },
    {
        "term": "Columna métrica",
        "definition": "Primera columna numérica detectada que no parece un identificador ni un código.",
    },
    {
        "term": "No medible",
        "definition": "Si falta la columna requerida, el hallazgo se omite. No se estima ni se inventa una cifra.",
    },
]



def _norm_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _fmt_money(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return "no medible"
    value = float(value)
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000:
        body = f"{absolute / 1_000_000:.2f}M"
    elif absolute >= 1_000:
        body = f"{absolute / 1_000:.1f}K"
    else:
        body = f"{absolute:,.0f}"
    return f"{sign}${body}"


def _fmt_pct(value: float, digits: int = 1) -> str:
    if value is None or not math.isfinite(float(value)):
        return "no medible"
    return f"{float(value) * 100:.{digits}f}%"


def _fmt_pp(value: float) -> str:
    """Diferencia entre dos porcentajes: se expresa en puntos porcentuales."""
    if value is None or not math.isfinite(float(value)):
        return "no medible"
    return f"{float(value) * 100:.1f} pp"


def _fmt_signed_pct(value: float, digits: int = 1) -> str:
    """Variación porcentual con signo explícito (crecimiento o caída)."""
    if value is None or not math.isfinite(float(value)):
        return "no medible"
    return f"{float(value) * 100:+.{digits}f}%"


def _fmt_count(value: float) -> str:
    return f"{int(round(float(value))):,}"


def _fmt_number(value: float, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def _fmt_days(value: float) -> str:
    return f"{float(value):.1f} días"


def _to_numeric(series: pd.Series) -> pd.Series:
    """Convierte monedas, porcentajes y paréntesis negativos a números."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").astype(float)

    raw = series.astype("string").str.strip()
    percent_mask = raw.str.contains("%", regex=False, na=False)
    negative_mask = raw.str.match(r"^\(.*\)$", na=False)
    text = raw.str.replace(r"[^\d,.\-]", "", regex=True)

    def parse_one(value: Any) -> Any:
        if pd.isna(value):
            return value
        text_value = str(value)
        if "," in text_value and "." in text_value:
            if text_value.rfind(",") > text_value.rfind("."):
                return text_value.replace(".", "").replace(",", ".")
            return text_value.replace(",", "")
        if "," in text_value:
            parts = text_value.split(",")
            if len(parts) == 2 and len(parts[1]) == 3:
                return text_value.replace(",", "")
            return text_value.replace(",", ".")
        return text_value

    parsed = pd.to_numeric(text.map(parse_one), errors="coerce").astype(float)
    parsed = parsed.where(~percent_mask, parsed / 100.0)
    parsed = parsed.where(~negative_mask, -parsed.abs())
    return parsed


def _score_role(column: str, role: str) -> int:
    normalized = _norm_name(column)
    aliases = ROLE_ALIASES[role]
    score = 0
    for alias in aliases:
        if normalized == alias:
            score = max(score, 120)
        elif normalized.startswith(alias + "_"):
            score = max(score, 80)
        elif normalized.endswith("_" + alias):
            score = max(score, 75)
        elif alias in normalized.split("_"):
            score = max(score, 60)
        elif alias in normalized:
            score = max(score, 30)

    if role in {"sales", "profit"} and any(
        token in normalized for token in ("margin", "margen", "ratio", "pct", "percent", "rate")
    ):
        score -= 90
    if role == "discount" and any(
        token in normalized for token in ("amount", "monto", "importe", "value")
    ):
        score -= 110
    if role == "date" and any(
        token in normalized for token in ("ship", "envio", "delivery", "despacho", "entrega")
    ):
        score -= 140
    if role == "order_id" and any(token in normalized for token in ("date", "fecha")):
        score -= 140
    return score


def detect_roles(df: pd.DataFrame) -> dict[str, Optional[str]]:
    """Detecta roles por nombre de columna, con reglas conservadoras."""
    roles: dict[str, Optional[str]] = {}
    for role in ROLE_ALIASES:
        best_column = None
        best_score = 0
        for column in df.columns:
            score = _score_role(str(column), role)
            if score > best_score:
                best_score = score
                best_column = str(column)
        roles[role] = best_column
    return roles


def _dedupe_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    quality: list[str] = []
    work = df.copy()
    work.columns = [str(column).strip() or "columna_sin_nombre" for column in work.columns]
    if work.columns.duplicated().any():
        duplicated = sorted(set(work.columns[work.columns.duplicated()].tolist()))
        quality.append(
            "Columnas duplicadas (" + ", ".join(duplicated[:5]) + "): se usó la primera aparición."
        )
        work = work.loc[:, ~work.columns.duplicated()].copy()
    return work, quality


def _select_dataframe(data: Any, primary_source_name: Optional[str]) -> tuple[pd.DataFrame, str]:
    if isinstance(data, pd.DataFrame):
        return data, "datos"

    if isinstance(data, dict):
        candidates: list[tuple[str, pd.DataFrame]] = [
            (str(name), value)
            for name, value in data.items()
            if isinstance(value, pd.DataFrame) and not value.empty
        ]
        if not candidates:
            raise AuditError("No hay tablas con datos para auditar.")
        if primary_source_name:
            for name, frame in candidates:
                if name == primary_source_name:
                    return frame, name
        # La tabla principal es la de mayor tamaño; el desempate es estable.
        name, frame = max(candidates, key=lambda item: (len(item[1]), len(item[1].columns)))
        return frame, name

    raise AuditError(
        "La auditoría Fase 1 trabaja con archivos CSV/Excel. "
        "El modo SQL todavía no está disponible para este flujo (P-03)."
    )


def _prepare_frame(
    df: pd.DataFrame,
    primary_source_name: Optional[str],
) -> tuple[pd.DataFrame, dict[str, Optional[str]], dict[str, Any], list[str]]:
    source_df, source_name = _select_dataframe(df, primary_source_name)
    work, quality = _dedupe_columns(source_df)
    if work.empty:
        raise AuditError("El dataset está vacío.")

    # Quitar filas completamente vacías no cambia las métricas, pero evita que
    # el perfil de calidad reporte un archivo más grande de lo que es.
    blank_rows = int(work.isna().all(axis=1).sum())
    if blank_rows:
        quality.append(f"{_fmt_count(blank_rows)} filas completamente vacías ignoradas.")
        work = work.dropna(how="all").copy()
    if work.empty:
        raise AuditError("El dataset no contiene filas con datos.")

    roles = detect_roles(work)
    work["__row"] = np.arange(len(work))

    for role, target in (("sales", "__sales"), ("profit", "__profit")):
        column = roles.get(role)
        if column:
            work[target] = _to_numeric(work[column])
            if not work[target].notna().any():
                quality.append(f"La columna '{column}' no contiene números utilizables; se ignora.")
                roles[role] = None
                work.drop(columns=[target], inplace=True)

    discount_column = roles.get("discount")
    if discount_column:
        discount = _to_numeric(work[discount_column])
        valid = discount.notna() & (discount >= 0)
        if discount[valid].max() > 1.5:
            if discount[valid].max() <= 100:
                discount = discount / 100.0
                quality.append(
                    f"'{discount_column}' se interpretó como porcentaje (0-100 → 0-1)."
                )
            else:
                quality.append(
                    f"'{discount_column}' tiene valores fuera de rango; no se usa para el análisis de descuento."
                )
                discount = pd.Series(np.nan, index=work.index, dtype=float)
        invalid_discount = int((discount.notna() & ((discount < 0) | (discount > 1))).sum())
        if invalid_discount:
            quality.append(f"{_fmt_count(invalid_discount)} valores de descuento fuera de 0-100% se ignoran.")
        work["__discount"] = discount.where((discount >= 0) & (discount <= 1))

    for role, target in (("date", "__date"), ("ship_date", "__ship_date")):
        column = roles.get(role)
        if not column:
            continue
        parsed = pd.to_datetime(work[column], errors="coerce")
        if getattr(parsed.dt, "tz", None) is not None:
            parsed = parsed.dt.tz_localize(None)
        valid_share = float(parsed.notna().mean()) if len(parsed) else 0.0
        if valid_share < 0.5:
            quality.append(
                f"La columna '{column}' parece de fecha, pero menos del 50% se pudo interpretar; se ignora."
            )
            roles[role] = None
            continue
        invalid_dates = int(parsed.isna().sum())
        if invalid_dates:
            quality.append(f"{_fmt_count(invalid_dates)} fechas inválidas en '{column}' se ignoran.")
        work[target] = parsed

    order_column = roles.get("order_id")
    # P-59: las ausencias de ventas/profit/descuento/orden solo se reportan
    # como calidad cuando hay contexto retail (alguna métrica de negocio
    # presente). En datasets de otro dominio listarlas es ruido: el dataset
    # no "falla" por no ser de ventas.
    has_retail_context = bool(roles.get("sales") or roles.get("profit"))
    if order_column:
        work["__order"] = work[order_column]
        orders = int(work["__order"].nunique(dropna=True))
        if orders == 0:
            quality.append("La columna de orden no contiene identificadores utilizables; se ignora.")
            roles["order_id"] = None
            work.drop(columns=["__order"], inplace=True)
    elif has_retail_context:
        quality.append("No se detectó identificador de orden; no se calculan métricas por orden.")

    if has_retail_context:
        if not roles.get("sales"):
            quality.append("No se detectó una columna de ventas; no se calculan ingresos ni márgenes.")
        if not roles.get("profit"):
            quality.append("No se detectó una columna de profit; no se calculan márgenes ni pérdidas.")
        if not roles.get("discount"):
            quality.append("No se detectó una columna de descuento; no se puede medir fuga por descuento.")

    missing_share = float(work.drop(columns=["__row"], errors="ignore").isna().mean().mean())
    if missing_share > 0.02:
        quality.append(f"{missing_share * 100:.1f}% de las celdas están vacías.")
    duplicate_rows = int(work.drop(columns=["__row"], errors="ignore").duplicated().sum())
    if duplicate_rows:
        row_word = "fila duplicada" if duplicate_rows == 1 else "filas duplicadas"
        quality.append(f"{_fmt_count(duplicate_rows)} {row_word} detectada{'s' if duplicate_rows != 1 else ''} (se conservan).")

    date_column = roles.get("date")
    date_start = date_end = None
    if date_column and "__date" in work:
        valid_dates = work["__date"].dropna()
        if not valid_dates.empty:
            date_start = valid_dates.min().date().isoformat()
            date_end = valid_dates.max().date().isoformat()

    orders = None
    if roles.get("order_id") and "__order" in work:
        orders = int(work["__order"].nunique(dropna=True))
        if orders < len(work):
            grain = "línea (varias líneas por orden)"
        else:
            grain = "registro (una fila por orden)"
    else:
        grain = "línea (sin identificador de orden)"

    profile = {
        "source_name": source_name,
        "rows": int(len(work)),
        "columns": int(len(source_df.columns)),
        "column_names": [str(column) for column in source_df.columns],
        "orders": orders,
        "date_start": date_start,
        "date_end": date_end,
        "grain": grain,
        "roles": {role: roles.get(role) for role in ROLE_ALIASES},
        "quality": quality,
    }
    return work, roles, profile, quality


def _margin(profit: float, sales: float) -> Optional[float]:
    if sales is None or not math.isfinite(float(sales)) or abs(float(sales)) < 1e-9:
        return None
    return float(profit) / float(sales)


def _add_fact(
    facts: list[AuditFact],
    *,
    fact_id: str,
    title: str,
    value: float,
    display_value: str,
    unit: str,
    category: str,
    severity: str,
    direction: str,
    definition: str,
    evidence: str,
    sample_size: int,
) -> None:
    facts.append(
        AuditFact(
            id=fact_id,
            title=title,
            value=float(value),
            display_value=display_value,
            unit=unit,
            category=category,
            severity=severity,
            direction=direction,
            definition=definition,
            evidence=evidence,
            sample_size=int(sample_size),
        )
    )


def _discount_analysis(df: pd.DataFrame, facts: list[AuditFact]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "threshold": None,
        "last_profitable": None,
        "levels": None,
        "deep_loss": None,
        "deep_sales_share": None,
        "deep_profit_share": None,
    }
    if "__discount" not in df or "__profit" not in df:
        return result

    subset = df.dropna(subset=["__discount", "__profit"]).copy()
    if subset.empty:
        return result

    subset["__discount_level"] = subset["__discount"].round(4)
    agg_spec: dict[str, Any] = {
        "rows": ("__row", "size"),
        "profit": ("__profit", "sum"),
    }
    if "__sales" in subset:
        agg_spec["sales"] = ("__sales", "sum")
    grouped = (
        subset.groupby("__discount_level", dropna=True)
        .agg(**agg_spec)
        .reset_index()
        .sort_values("__discount_level")
    )
    if "sales" not in grouped:
        grouped["sales"] = np.nan
    grouped["margin"] = np.where(grouped["sales"].abs() > 1e-9, grouped["profit"] / grouped["sales"], np.nan)
    grouped["negative_share"] = (
        subset.assign(__negative=subset["__profit"] < 0)
        .groupby("__discount_level")["__negative"]
        .mean()
        .reindex(grouped["__discount_level"])
        .values
    )
    result["available"] = True
    result["levels"] = grouped
    total_profit = float(df["__profit"].sum())
    total_sales = float(df["__sales"].sum()) if "__sales" in df else None

    min_rows = max(10, int(len(subset) * 0.001))
    eligible = grouped[grouped["rows"] >= min_rows].copy()
    loss_levels = eligible[eligible["profit"] < 0].sort_values("__discount_level")
    profit_levels = eligible[eligible["profit"] > 0].sort_values("__discount_level")

    threshold = None
    if not loss_levels.empty:
        threshold = float(loss_levels.iloc[0]["__discount_level"])
        result["threshold"] = threshold
        deep = subset[subset["__discount_level"] >= threshold]
        deep_loss = float(deep["__profit"].sum())
        deep_rows = int(len(deep))
        deep_sales = float(deep["__sales"].sum()) if "__sales" in deep else None
        deep_sales_share = deep_sales / total_sales if total_sales and total_sales > 0 else None
        # La pérdida del tramo es negativa; el peso se expresa como magnitud
        # ("equivale a 47% del profit neto"), no como un porcentaje negativo.
        deep_profit_share = abs(deep_loss) / total_profit if total_profit > 0 else None
        result.update(
            {
                "deep_loss": deep_loss,
                "deep_rows": deep_rows,
                "deep_sales_share": deep_sales_share,
                "deep_profit_share": deep_profit_share,
            }
        )
        share_text = f" · {_fmt_pct(deep_profit_share)} del profit neto" if deep_profit_share is not None else ""
        _add_fact(
            facts,
            fact_id="DISC-03",
            title="Umbral de descuento que destruye margen",
            value=threshold,
            display_value=_fmt_pct(threshold),
            unit="%",
            category="descuentos",
            severity="alta",
            direction="negative",
            definition=(
                "Primer nivel exacto de descuento, con al menos "
                f"{min_rows} líneas, cuyo profit agregado es negativo. "
                "Un descuento mayor no siempre es peor: se evalúa cada nivel."
            ),
            evidence=(
                "profit.groupby(discount).sum(); "
                f"niveles con n>={min_rows}; primer profit < 0"
            ),
            sample_size=deep_rows,
        )
        _add_fact(
            facts,
            fact_id="DISC-04",
            title=f"Profit del tramo ≥{_fmt_pct(threshold)} de descuento",
            value=deep_loss,
            display_value=f"{_fmt_money(deep_loss)}{share_text}",
            unit="USD",
            category="descuentos",
            severity="alta",
            direction="negative" if deep_loss < 0 else "positive",
            definition=(
                f"Suma del profit de todas las líneas con descuento mayor o igual a {_fmt_pct(threshold)}. "
                "Es el resultado agregado del tramo, no la pérdida bruta."
            ),
            evidence=(
                f"sum(profit) donde discount >= {threshold:.4f}; "
                f"{_fmt_count(deep_rows)} líneas"
            ),
            sample_size=deep_rows,
        )

        if deep_sales_share is not None:
            _add_fact(
                facts,
                fact_id="DISC-05",
                title=f"Peso del tramo ≥{_fmt_pct(threshold)} en ventas",
                value=deep_sales_share,
                display_value=_fmt_pct(deep_sales_share),
                unit="%",
                category="descuentos",
                severity="media",
                direction="neutral",
                definition="Ventas del tramo con descuento profundo dividido entre las ventas totales.",
                evidence=f"sum(sales) del tramo / sum(sales) total; n={_fmt_count(deep_rows)}",
                sample_size=deep_rows,
            )

    if not profit_levels.empty:
        last_profitable = float(profit_levels.iloc[-1]["__discount_level"])
        result["last_profitable"] = last_profitable
        last_profit = float(profit_levels.iloc[-1]["profit"])
        _add_fact(
            facts,
            fact_id="DISC-06",
            title="Último nivel de descuento que sigue siendo rentable",
            value=last_profitable,
            display_value=_fmt_pct(last_profitable),
            unit="%",
            category="descuentos",
            severity="media",
            direction="positive",
            definition=(
                "Nivel exacto más alto, con al menos "
                f"{min_rows} líneas, cuyo profit agregado sigue siendo positivo. "
                "No implica que sea el nivel óptimo; solo que no pierde dinero."
            ),
            evidence=(
                f"profit del nivel = {_fmt_money(last_profit)}; "
                f"n={int(profit_levels.iloc[-1]['rows'])}"
            ),
            sample_size=int(profit_levels.iloc[-1]["rows"]),
        )

    if "__sales" in subset:
        no_discount = subset[subset["__discount"] <= 1e-9]
        with_discount = subset[subset["__discount"] > 1e-9]
        if not no_discount.empty:
            no_profit = float(no_discount["__profit"].sum())
            _add_fact(
                facts,
                fact_id="DISC-01",
                title="Profit de las líneas sin descuento",
                value=no_profit,
                display_value=_fmt_money(no_profit),
                unit="USD",
                category="descuentos",
                severity="info",
                direction="positive" if no_profit >= 0 else "negative",
                definition="Suma del profit de las líneas cuyo descuento es 0%.",
                evidence=f"sum(profit) donde discount == 0; n={_fmt_count(len(no_discount))}",
                sample_size=int(len(no_discount)),
            )
        if not with_discount.empty:
            with_profit = float(with_discount["__profit"].sum())
            _add_fact(
                facts,
                fact_id="DISC-02",
                title="Profit de las líneas con descuento",
                value=with_profit,
                display_value=_fmt_money(with_profit),
                unit="USD",
                category="descuentos",
                severity="media",
                direction="positive" if with_profit >= 0 else "negative",
                definition="Suma del profit de todas las líneas con descuento mayor que 0%.",
                evidence=f"sum(profit) donde discount > 0; n={_fmt_count(len(with_discount))}",
                sample_size=int(len(with_discount)),
            )

    max_discount = float(subset["__discount"].max())
    if max_discount >= 0.5:
        extreme = subset[subset["__discount"] >= 0.5]
        extreme_loss = float(extreme["__profit"].sum())
        extreme_sales_share = None
        if "__sales" in subset and total_sales and total_sales > 0:
            extreme_sales_share = float(extreme["__sales"].sum()) / total_sales
        share_text = (
            f" · {_fmt_pct(extreme_sales_share)} de las ventas"
            if extreme_sales_share is not None
            else ""
        )
        _add_fact(
            facts,
            fact_id="DISC-07",
            title="Profit del tramo ≥50% de descuento",
            value=extreme_loss,
            display_value=f"{_fmt_money(extreme_loss)}{share_text}",
            unit="USD",
            category="descuentos",
            severity="alta",
            direction="negative" if extreme_loss < 0 else "positive",
            definition="Suma del profit de las líneas con descuento de 50% o más.",
            evidence=f"sum(profit) donde discount >= 0.50; n={_fmt_count(len(extreme))}",
            sample_size=int(len(extreme)),
        )
    return result


def _loss_facts(df: pd.DataFrame, facts: list[AuditFact]) -> None:
    if "__profit" not in df:
        return
    profit = df["__profit"].dropna()
    if profit.empty:
        return
    total_profit = float(profit.sum())
    negative = profit[profit < 0]
    negative_loss = float(negative.sum())
    negative_count = int(len(negative))
    negative_share = negative_count / len(profit) if len(profit) else 0.0

    _add_fact(
        facts,
        fact_id="LOSS-01",
        title="Líneas con profit negativo",
        value=negative_count,
        display_value=f"{_fmt_count(negative_count)} ({_fmt_pct(negative_share)})",
        unit="count",
        category="pérdidas",
        severity="alta",
        direction="negative",
        definition="Cantidad de líneas cuyo profit es menor que cero. Una línea negativa no implica que la orden completa sea negativa.",
        evidence=f"profit < 0; n={_fmt_count(negative_count)} de {_fmt_count(len(profit))}",
        sample_size=len(profit),
    )
    _add_fact(
        facts,
        fact_id="LOSS-02",
        title="Pérdida bruta acumulada",
        value=negative_loss,
        display_value=_fmt_money(negative_loss),
        unit="USD",
        category="pérdidas",
        severity="alta",
        direction="negative",
        definition=(
            "Suma solo de los profits negativos. No es el profit neto: "
            "las líneas positivas compensan parte de esta pérdida."
        ),
        evidence=f"sum(profit) donde profit < 0; n={_fmt_count(negative_count)}",
        sample_size=negative_count,
    )
    if "__sales" in df:
        sales = df["__sales"].dropna()
        total_sales = float(sales.sum())
        negative_sales = float(df.loc[df["__profit"] < 0, "__sales"].sum())
        negative_sales_share = negative_sales / total_sales if total_sales > 0 else None
        if negative_sales_share is not None:
            _add_fact(
                facts,
                fact_id="LOSS-03",
                title="Ventas que provienen de líneas con pérdida",
                value=negative_sales_share,
                display_value=_fmt_pct(negative_sales_share),
                unit="%",
                category="pérdidas",
                severity="media",
                direction="neutral",
                definition="Ventas de las líneas con profit negativo dividido entre las ventas totales.",
                evidence="sum(sales) donde profit < 0 / sum(sales)",
                sample_size=negative_count,
            )

    if "__order" in df:
        order_spec: dict[str, Any] = {
            "profit": ("__profit", "sum"),
            "rows": ("__row", "size"),
        }
        if "__sales" in df:
            order_spec["sales"] = ("__sales", "sum")
        orders = df.dropna(subset=["__order"]).groupby("__order").agg(**order_spec)
        if not orders.empty:
            negative_orders = orders[orders["profit"] < 0]
            negative_order_share = len(negative_orders) / len(orders)
            _add_fact(
                facts,
                fact_id="LOSS-04",
                title="Órdenes con profit neto negativo",
                value=len(negative_orders),
                display_value=f"{_fmt_count(len(negative_orders))} ({_fmt_pct(negative_order_share)})",
                unit="count",
                category="pérdidas",
                severity="alta",
                direction="negative",
                definition=(
                    "Cantidad de órdenes cuya suma de profit es negativa. "
                    "Es distinto de contar líneas negativas: una orden puede tener una línea negativa y aun así ser rentable."
                ),
                evidence=(
                    "profit.groupby(order_id).sum() < 0; "
                    f"n={_fmt_count(len(negative_orders))} de {_fmt_count(len(orders))}"
                ),
                sample_size=len(orders),
            )
            if "__sales" in orders:
                negative_order_sales = float(negative_orders["sales"].sum())
                total_order_sales = float(orders["sales"].sum())
                if total_order_sales > 0:
                    _add_fact(
                        facts,
                        fact_id="LOSS-05",
                        title="Ventas en órdenes con profit neto negativo",
                        value=negative_order_sales,
                        display_value=f"{_fmt_money(negative_order_sales)} ({_fmt_pct(negative_order_sales / total_order_sales)})",
                        unit="USD",
                        category="pérdidas",
                        severity="media",
                        direction="negative",
                        definition="Ventas de las órdenes cuyo profit agregado es negativo.",
                        evidence="sum(sales) de órdenes con profit < 0",
                        sample_size=len(negative_orders),
                    )

            any_negative = (
                df.dropna(subset=["__order"])
                .assign(__negative_line=df["__profit"] < 0)
                .groupby("__order")["__negative_line"]
                .any()
            )
            any_negative_count = int(any_negative.sum())
            any_negative_share = any_negative_count / len(orders) if len(orders) else 0.0
            _add_fact(
                facts,
                fact_id="LOSS-06",
                title="Órdenes con al menos una línea negativa",
                value=any_negative_count,
                display_value=f"{_fmt_count(any_negative_count)} ({_fmt_pct(any_negative_share)})",
                unit="count",
                category="pérdidas",
                severity="media",
                direction="negative",
                definition=(
                    "Órdenes que contienen una o más líneas con profit negativo, aunque la orden "
                    "complete sea rentable. No es lo mismo que una orden con profit neto negativo."
                ),
                evidence="any(profit < 0).groupby(order_id); comparar con LOSS-04 (suma por orden)",
                sample_size=len(orders),
            )


def _group_metrics(
    df: pd.DataFrame,
    dimension: str,
    min_rows: int,
    min_sales: float,
    deep_threshold: float = 0.5,
) -> Optional[pd.DataFrame]:
    if "__profit" not in df or "__sales" not in df or dimension not in df:
        return None
    subset = df.dropna(subset=[dimension, "__profit", "__sales"]).copy()
    if subset.empty:
        return None
    agg = (
        subset.groupby(dimension, dropna=True)
        .agg(
            rows=("__row", "size"),
            sales=("__sales", "sum"),
            profit=("__profit", "sum"),
        )
        .reset_index()
    )
    agg["margin"] = np.where(agg["sales"].abs() > 1e-9, agg["profit"] / agg["sales"], np.nan)
    agg["negative_rows"] = (
        subset.assign(__negative=subset["__profit"] < 0)
        .groupby(dimension)["__negative"]
        .sum()
        .reindex(agg[dimension])
        .values
    )
    agg["negative_share"] = np.where(agg["rows"] > 0, agg["negative_rows"] / agg["rows"], np.nan)
    if "__discount" in subset:
        discount_agg = (
            subset.assign(__deep=subset["__discount"] >= deep_threshold)
            .groupby(dimension)["__deep"]
            .mean()
            .reindex(agg[dimension])
            .values
        )
        agg["deep_discount_share"] = discount_agg
    else:
        agg["deep_discount_share"] = np.nan
    filtered = agg[(agg["rows"] >= min_rows) & (agg["sales"] > min_sales)].copy()
    if filtered.empty:
        filtered = agg[(agg["sales"] > 0) & (agg["rows"] > 0)].copy()
    return filtered.sort_values("profit", ascending=True)


def _segment_facts(
    df: pd.DataFrame,
    roles: dict[str, Optional[str]],
    facts: list[AuditFact],
    deep_threshold: float = 0.5,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "subcategory": None,
        "category": None,
        "region": None,
        "region_discount_gap": None,
        "lead_time": None,
    }
    if "__profit" not in df or "__sales" not in df:
        return result
    min_rows = max(3, int(len(df) * 0.005))
    min_sales = max(0.0, float(df["__sales"].sum()) * 0.005)

    sub_col = roles.get("subcategory")
    if sub_col:
        groups = _group_metrics(df, sub_col, min_rows, min_sales, deep_threshold=deep_threshold)
        if groups is not None and not groups.empty:
            result["subcategory"] = groups
            worst = groups.iloc[0]
            worst_profit = float(worst["profit"])
            worst_margin = float(worst["margin"]) if pd.notna(worst["margin"]) else None
            display = f"{_fmt_money(worst_profit)}"
            if worst_margin is not None:
                display += f" · margen {_fmt_pct(worst_margin)}"
            _add_fact(
                facts,
                fact_id="SEG-01",
                title=f"Subcategoría con menor profit: {worst[sub_col]}",
                value=worst_profit,
                display_value=display,
                unit="USD",
                category="segmentos",
                severity="alta" if worst_profit < 0 else "media",
                direction="negative" if worst_profit < 0 else "positive",
                definition=(
                    f"Suma de profit de la subcategoría '{worst[sub_col]}' con ventas de "
                    f"{_fmt_money(float(worst['sales']))} y {int(worst['rows'])} líneas. "
                    f"Se excluyen grupos con menos de {min_rows} líneas o ventas por debajo de {_fmt_money(min_sales)}."
                ),
                evidence=f"profit.groupby({sub_col}).sum(); grupo con menor profit",
                sample_size=int(worst["rows"]),
            )

    cat_col = roles.get("category")
    if cat_col:
        groups = _group_metrics(df, cat_col, min_rows, min_sales, deep_threshold=deep_threshold)
        if groups is not None and not groups.empty:
            result["category"] = groups
            by_margin = groups.dropna(subset=["margin"]).sort_values("margin", ascending=True)
            if by_margin.empty:
                by_margin = groups.sort_values("margin", ascending=True, na_position="last")
            worst = by_margin.iloc[0]
            best = by_margin.iloc[-1]
            _add_fact(
                facts,
                fact_id="SEG-02",
                title=f"Categoría con menor margen: {worst[cat_col]}",
                value=float(worst["margin"]) if pd.notna(worst["margin"]) else 0.0,
                display_value=(
                    f"{_fmt_pct(float(worst['margin']))} · profit {_fmt_money(float(worst['profit']))}"
                    if pd.notna(worst["margin"])
                    else "no medible"
                ),
                unit="%",
                category="segmentos",
                severity="alta" if pd.notna(worst["margin"]) and float(worst["margin"]) < 0.05 else "media",
                direction="negative" if pd.notna(worst["margin"]) and float(worst["margin"]) < 0.05 else "neutral",
                definition=(
                    f"Margen de la categoría '{worst[cat_col]}' (profit / ventas). "
                    f"Ventas: {_fmt_money(float(worst['sales']))}. No es el margen promedio de sus líneas."
                ),
                evidence=f"profit.groupby({cat_col}).sum() / sales.groupby({cat_col}).sum()",
                sample_size=int(worst["rows"]),
            )
            if best[cat_col] != worst[cat_col] and pd.notna(best["margin"]):
                _add_fact(
                    facts,
                    fact_id="SEG-03",
                    title=f"Mejor margen por categoría: {best[cat_col]}",
                    value=float(best["margin"]),
                    display_value=f"{_fmt_pct(float(best['margin']))} · profit {_fmt_money(float(best['profit']))}",
                    unit="%",
                    category="segmentos",
                    severity="info",
                    direction="positive",
                    definition=f"Mayor margen agregado entre las categorías con volumen suficiente: '{best[cat_col]}'.",
                    evidence=f"profit.groupby({cat_col}).sum() / sales.groupby({cat_col}).sum()",
                    sample_size=int(best["rows"]),
                )

    region_col = roles.get("region")
    if region_col:
        groups = _group_metrics(df, region_col, min_rows, min_sales, deep_threshold=deep_threshold)
        if groups is not None and not groups.empty:
            result["region"] = groups
            by_margin = groups.dropna(subset=["margin"]).sort_values("margin", ascending=True)
            if by_margin.empty:
                by_margin = groups.sort_values("margin", ascending=True, na_position="last")
            worst = by_margin.iloc[0]
            best = by_margin.iloc[-1]
            if pd.notna(worst["margin"]):
                _add_fact(
                    facts,
                    fact_id="REG-01",
                    title=f"Región con menor margen: {worst[region_col]}",
                    value=float(worst["margin"]),
                    display_value=(
                        f"{_fmt_pct(float(worst['margin']))} · profit {_fmt_money(float(worst['profit']))}"
                    ),
                    unit="%",
                    category="segmentos",
                    severity="alta" if float(worst["margin"]) < 0.08 else "media",
                    direction="negative" if float(worst["margin"]) < 0.08 else "neutral",
                    definition=(
                        f"Margen agregado de la región '{worst[region_col]}'. "
                        f"Ventas: {_fmt_money(float(worst['sales']))}; líneas: {int(worst['rows'])}."
                    ),
                    evidence=f"profit.groupby({region_col}).sum() / sales.groupby({region_col}).sum()",
                    sample_size=int(worst["rows"]),
                )
            if pd.notna(best["margin"]) and pd.notna(worst["margin"]) and best[region_col] != worst[region_col]:
                gap = float(best["margin"]) - float(worst["margin"])
                if gap >= 0.005:
                    _add_fact(
                        facts,
                        fact_id="REG-02",
                        title="Brecha de margen entre regiones",
                        value=gap,
                        display_value=f"{_fmt_pp(gap)} ({best[region_col]} vs {worst[region_col]})",
                        unit="pp",
                        category="segmentos",
                        severity="alta" if gap >= 0.05 else "media",
                        direction="negative" if gap >= 0.05 else "neutral",
                        definition=(
                            "Diferencia de margen entre la mejor y la peor región con volumen suficiente. "
                            "Se mide en puntos porcentuales, no como crecimiento."
                        ),
                        evidence="max(margin) - min(margin) entre regiones elegibles",
                        sample_size=int(best["rows"] + worst["rows"]),
                    )
                    if "deep_discount_share" in groups and pd.notna(worst["deep_discount_share"]) and pd.notna(best["deep_discount_share"]):
                        discount_gap = float(worst["deep_discount_share"]) - float(best["deep_discount_share"])
                        result["region_discount_gap"] = discount_gap
                        _add_fact(
                            facts,
                            fact_id="REG-03",
                            title=f"Brecha de descuento ≥{_fmt_pct(deep_threshold)} entre regiones",
                            value=discount_gap,
                            display_value=f"{_fmt_pp(discount_gap)} ({worst[region_col]} vs {best[region_col]})",
                            unit="pp",
                            category="descuentos",
                            severity="alta" if discount_gap >= 0.10 else "media",
                            direction="negative" if discount_gap > 0.05 else "neutral",
                            definition=(
                                f"Diferencia en la proporción de líneas con descuento ≥{_fmt_pct(deep_threshold)} "
                                "entre la peor y la mejor región por margen. "
                                "Ayuda a separar el efecto precio del efecto mezcla de productos."
                            ),
                            evidence=f"mean(discount >= {deep_threshold:.4f}).groupby(region)",
                            sample_size=int(worst["rows"] + best["rows"]),
                        )

    date_col = roles.get("date")
    ship_col = roles.get("ship_date")
    if date_col and ship_col and "__date" in df and "__ship_date" in df and region_col:
        with_dates = df.dropna(subset=["__date", "__ship_date", region_col]).copy()
        if not with_dates.empty:
            lead = (with_dates["__ship_date"] - with_dates["__date"]).dt.total_seconds() / 86400.0
            with_dates["__lead_days"] = lead
            lead_by_region = (
                with_dates.groupby(region_col)["__lead_days"]
                .agg(["mean", "count"])
                .reset_index()
                .sort_values("mean", ascending=False)
            )
            lead_by_region = lead_by_region[lead_by_region["count"] >= min_rows]
            if not lead_by_region.empty:
                worst_lead = lead_by_region.iloc[0]
                result["lead_time"] = lead_by_region
                _add_fact(
                    facts,
                    fact_id="REG-04",
                    title=f"Mayor tiempo de entrega: {worst_lead[region_col]}",
                    value=float(worst_lead["mean"]),
                    display_value=_fmt_days(float(worst_lead["mean"])),
                    unit="days",
                    category="operaciones",
                    severity="media",
                    direction="neutral",
                    definition=(
                        "Promedio de días entre la fecha de pedido y la fecha de envío. "
                        "Solo se calcula si ambas fechas son válidas y la región tiene volumen suficiente."
                    ),
                    evidence=f"mean(ship_date - order_date).groupby({region_col})",
                    sample_size=int(worst_lead["count"]),
                )
    return result


def _customer_facts(
    df: pd.DataFrame,
    roles: dict[str, Optional[str]],
    facts: list[AuditFact],
) -> dict[str, Any]:
    result: dict[str, Any] = {"customers": None, "top_loss": None}
    customer_col = roles.get("customer")
    if not customer_col or "__profit" not in df:
        return result
    subset = df.dropna(subset=[customer_col, "__profit"]).copy()
    if subset.empty:
        return result
    customer_spec: dict[str, Any] = {
        "rows": ("__row", "size"),
        "profit": ("__profit", "sum"),
    }
    if "__sales" in subset:
        customer_spec["sales"] = ("__sales", "sum")
    groups = subset.groupby(customer_col, dropna=True).agg(**customer_spec).reset_index()
    if "sales" not in groups:
        groups["sales"] = np.nan
    groups["margin"] = np.where(groups["sales"].abs() > 1e-9, groups["profit"] / groups["sales"], np.nan)
    result["customers"] = groups
    negative = groups[groups["profit"] < 0].sort_values("profit", ascending=True)
    if negative.empty:
        _add_fact(
            facts,
            fact_id="CUST-01",
            title="Clientes con profit negativo",
            value=0,
            display_value="0 clientes",
            unit="count",
            category="clientes",
            severity="info",
            direction="positive",
            definition="Clientes cuya suma de profit en todo el periodo es menor que cero.",
            evidence=f"profit.groupby({customer_col}).sum() < 0",
            sample_size=len(groups),
        )
        return result

    total_negative_loss = float(negative["profit"].sum())
    _add_fact(
        facts,
        fact_id="CUST-01",
        title="Clientes con profit negativo",
        value=float(len(negative)),
        display_value=f"{_fmt_count(len(negative))} clientes · {_fmt_money(total_negative_loss)}",
        unit="count",
        category="clientes",
        severity="alta",
        direction="negative",
        definition=(
            "Clientes cuya suma de profit en todo el periodo es menor que cero. "
            "La pérdida mostrada es la suma de sus profits negativos netos; no es el profit total."
        ),
        evidence=f"profit.groupby({customer_col}).sum() < 0; n={_fmt_count(len(groups))}",
        sample_size=len(groups),
    )
    top10 = negative.head(10)
    top10_loss = float(top10["profit"].sum())
    top10_share = top10_loss / total_negative_loss if total_negative_loss < 0 else None
    if top10_share is not None:
        _add_fact(
            facts,
            fact_id="CUST-02",
            title="Concentración de la pérdida en los 10 peores clientes",
            value=top10_share,
            display_value=f"{_fmt_pct(top10_share)} · {_fmt_money(top10_loss)}",
            unit="%",
            category="clientes",
            severity="alta" if top10_share >= 0.3 else "media",
            direction="negative",
            definition=(
                "Porcentaje de la pérdida acumulada por clientes negativos que concentran los 10 clientes "
                "con menor profit. Se calcula sobre la pérdida de clientes, no sobre el profit neto."
            ),
            evidence=f"sum(top10 profit < 0) / sum(all negative customer profit)",
            sample_size=len(top10),
        )
    result["top_loss"] = negative.head(10)
    return result


def _time_facts(
    df: pd.DataFrame,
    roles: dict[str, Optional[str]],
    facts: list[AuditFact],
) -> dict[str, Any]:
    result: dict[str, Any] = {"years": None, "growth_sales": None, "growth_profit": None}
    if not roles.get("date") or "__date" not in df or "__profit" not in df:
        return result
    subset = df.dropna(subset=["__date", "__profit"]).copy()
    if subset.empty:
        return result
    subset["__year"] = subset["__date"].dt.year
    year_spec: dict[str, Any] = {
        "rows": ("__row", "size"),
        "profit": ("__profit", "sum"),
    }
    if "__sales" in subset:
        year_spec["sales"] = ("__sales", "sum")
    agg = subset.groupby("__year").agg(**year_spec).reset_index().sort_values("__year")
    if len(agg) < 2:
        return result
    if "sales" not in agg:
        agg["sales"] = np.nan
    agg["margin"] = np.where(agg["sales"].abs() > 1e-9, agg["profit"] / agg["sales"], np.nan)
    result["years"] = agg
    first = agg.iloc[0]
    last = agg.iloc[-1]
    if pd.notna(first["sales"]) and float(first["sales"]) != 0:
        growth_sales = float(last["sales"]) / float(first["sales"]) - 1.0
        result["growth_sales"] = growth_sales
        _add_fact(
            facts,
            fact_id="TIME-01",
            title=f"Crecimiento de ventas {int(first['__year'])} → {int(last['__year'])}",
            value=growth_sales,
            display_value=_fmt_signed_pct(growth_sales),
            unit="%",
            category="crecimiento",
            severity="media",
            direction="positive" if growth_sales >= 0 else "negative",
            definition="Variación porcentual de las ventas entre el primer y el último año con datos.",
            evidence=f"sales.year.last / sales.year.first - 1; {int(first['__year'])}-{int(last['__year'])}",
            sample_size=int(last["rows"]),
        )
    if pd.notna(first["margin"]) and pd.notna(last["margin"]):
        margin_delta = float(last["margin"]) - float(first["margin"])
        margin_direction = "neutral" if abs(margin_delta) < 0.0005 else ("negative" if margin_delta < 0 else "positive")
        _add_fact(
            facts,
            fact_id="TIME-02",
            title=f"Margen {int(first['__year'])} → {int(last['__year'])}",
            value=margin_delta,
            display_value=(
                f"{_fmt_pct(float(first['margin']))} → {_fmt_pct(float(last['margin']))} "
                f"({margin_delta * 100:+.1f} pp)"
            ),
            unit="pp",
            category="crecimiento",
            severity="alta" if margin_delta <= -0.02 else "info",
            direction=margin_direction,
            definition="Cambio del margen agregado entre el primer y el último año. No es una tendencia de todos los años.",
            evidence="profit/sales por año; comparación primer vs último año",
            sample_size=int(last["rows"]),
        )
    if len(agg) >= 2:
        previous = agg.iloc[-2]
        latest_margin_delta = (
            float(last["margin"]) - float(previous["margin"])
            if pd.notna(last["margin"]) and pd.notna(previous["margin"])
            else None
        )
        if latest_margin_delta is not None:
            latest_direction = "neutral" if abs(latest_margin_delta) < 0.0005 else ("negative" if latest_margin_delta < 0 else "positive")
            _add_fact(
                facts,
                fact_id="TIME-03",
                title=f"Margen del último año ({int(last['__year'])})",
                value=float(last["margin"]) if pd.notna(last["margin"]) else 0.0,
                display_value=(
                    f"{_fmt_pct(float(last['margin']))} "
                    f"({latest_margin_delta * 100:+.1f} pp vs {int(previous['__year'])})"
                ),
                unit="%",
                category="crecimiento",
                severity="alta" if latest_margin_delta <= -0.02 else "info",
                direction=latest_direction,
                definition="Margen del último año y variación en puntos porcentuales frente al año anterior.",
                evidence="profit/sales del último año vs el anterior",
                sample_size=int(last["rows"]),
            )
    return result


def _looks_categoric(series: pd.Series) -> bool:
    """Filtros que debe pasar cualquier columna usada para composición."""
    if pd.api.types.is_numeric_dtype(series):
        return False
    valid = series.dropna()
    if valid.empty or not (2 <= valid.nunique() <= 50):
        return False
    if float(valid.astype(str).str.len().mean()) > 60:
        return False
    if float(valid.astype(str).str.match(r"^\d+([.\-/]\d+)*$").mean()) > 0.8:
        return False
    return True


def _is_identifier_like(normalized: str) -> bool:
    """True si el nombre normalizado parece id/código/coordenada/periodo."""
    if normalized == "id" or normalized.endswith("_id") or normalized.startswith("id_"):
        return True
    if "codigo" in normalized or "code" in normalized or normalized.endswith("cod"):
        return True
    if "key" in normalized or "uuid" in normalized or "hash" in normalized:
        return True
    if any(token in normalized for token in ("coord", "latitude", "longitude", "_lat", "_lon", "zip", "postal")):
        return True
    return False


def _is_time_dimension(normalized: str) -> bool:
    """Columnas de dimensión temporal: no son métricas aunque sean numéricas
    (año, trimestre). Un 'promedio de periodo' no significa nada."""
    return any(
        token in normalized
        for token in (
            "periodo", "period", "year", "anio", "ano", "mes", "month",
            "trimestre", "quarter", "fecha", "date", "dia", "day", "semana", "week",
        )
    )


def _pick_categoric_column(work: pd.DataFrame, roles: dict[str, Optional[str]]) -> Optional[str]:
    """Columna categórica para composición: primero los roles conocidos
    (región, categoría, cliente, producto) y después cualquier columna de
    texto con cardinalidad razonable. Los roles también deben pasar los
    filtros: un 'departamento' numérico o un código de país no son categorías
    legibles para el usuario."""
    for role in ("region", "category", "customer", "product"):
        column = roles.get(role)
        if column and column in work.columns:
            normalized = _norm_name(column)
            if not _is_identifier_like(normalized) and _looks_categoric(work[column]):
                return str(column)
    excluded = {
        roles.get(role_name)
        for role_name in ("order_id", "date", "ship_date", "sales", "profit", "discount")
    }
    excluded.discard(None)
    for column in work.columns:
        if column.startswith("__") or column in excluded:
            continue
        normalized = _norm_name(column)
        if _is_identifier_like(normalized) or _is_time_dimension(normalized):
            continue
        if _looks_categoric(work[column]):
            return str(column)
    return None


# Tokens que indican una columna de MEDIDA real. Si ninguna columna numérica
# encaja, no se publican promedios/medianas: un hecho falso es peor que
# ninguno (P-59).
METRIC_TOKENS = (
    "valor", "value", "total", "monto", "importe", "precio", "price", "costo",
    "cost", "tarifa", "tasa", "rate", "cantidad", "count", "conteo", "casos",
    "unidades", "units", "qty", "quantity", "edad", "ventas", "venta",
    "revenue", "ingresos", "ingreso", "profit", "beneficio", "utilidad",
    "ganancia", "salario", "sueldo", "poblacion", "population", "muertes",
    "deaths", "hospitalizaciones", "temperatura", "precipitacion", "defunciones",
)


def _pick_metric_column(work: pd.DataFrame, roles: dict[str, Optional[str]]) -> Optional[str]:
    """Columna numérica utilizable como métrica, con reglas conservadoras:
    - El nombre debe parecer una medida (lista blanca METRIC_TOKENS).
    - Se excluyen columnas con rol semántico detectado (códigos de región o
      categoría suelen ser numéricos y su promedio no significa nada).
    - Columnas de texto solo si >90% de los valores encajan en un patrón
      numérico estricto (evita extraer dígitos de etiquetas como
      'De 25 a 29 años').
    """
    excluded = {
        roles.get(role_name)
        for role_name in ("order_id", "date", "ship_date", "sales", "profit", "discount")
    }
    excluded.discard(None)
    semantic_columns = {
        roles.get(role_name)
        for role_name in ("region", "category", "subcategory", "customer", "product")
    }
    semantic_columns.discard(None)
    for column in work.columns:
        if column.startswith("__") or column in excluded or column in semantic_columns:
            continue
        normalized = _norm_name(column)
        if _is_identifier_like(normalized) or _is_time_dimension(normalized):
            continue
        if not any(token in normalized for token in METRIC_TOKENS):
            continue
        series = work[column]
        valid: Optional[pd.Series] = None
        if pd.api.types.is_numeric_dtype(series):
            valid = pd.to_numeric(series, errors="coerce").dropna()
        else:
            raw = series.dropna().astype(str).str.strip()
            if len(raw) and float(raw.str.match(r"^-?\d+([.,]\d+)?$").mean()) > 0.9:
                valid = _to_numeric(series).dropna()
        if valid is None or len(valid) < 2 or valid.nunique() <= 1:
            continue
        if len(valid) < 0.5 * len(series) and len(valid) < 10:
            continue
        return str(column)
    return None


def _generic_facts(
    work: pd.DataFrame,
    roles: dict[str, Optional[str]],
    profile: dict[str, Any],
) -> list[AuditFact]:
    """Hechos verificables para datasets sin ventas ni profit (P-59).

    No especializa por dominio: calcula composición, actividad temporal y
    estadísticos de las columnas disponibles. Cada cifra es determinista con
    pandas y lleva id, definición y evidencia.
    """
    facts: list[AuditFact] = []
    rows = int(profile.get("rows") or len(work))

    if "__date" in work:
        dates = work["__date"].dropna()
        if len(dates):
            month_counts = dates.dt.to_period("M").value_counts().sort_index()
            peak_month = month_counts.idxmax()
            peak_n = int(month_counts.max())
            _add_fact(
                facts,
                fact_id="TIME-G01",
                title="Mes con más registros",
                value=float(peak_n),
                display_value=f"{peak_month} ({_fmt_count(peak_n)} registros, {_fmt_pct(peak_n / len(dates))})",
                unit="registros",
                category="actividad",
                severity="info",
                direction="neutral",
                definition=(
                    "Año-mes con mayor número de registros. La participación se calcula "
                    f"sobre las {_fmt_count(len(dates))} fechas válidas."
                ),
                evidence=f"value_counts por año-mes sobre '{roles.get('date')}'",
                sample_size=len(dates),
            )
            year_counts = dates.dt.year.value_counts().sort_index()
            if len(year_counts) >= 2:
                first_year, last_year = int(year_counts.index[0]), int(year_counts.index[-1])
                first_n, last_n = int(year_counts.iloc[0]), int(year_counts.iloc[-1])
                growth = (last_n - first_n) / first_n if first_n else None
                display = (
                    f"{first_year}: {_fmt_count(first_n)} → {last_year}: {_fmt_count(last_n)}"
                    + (f" ({_fmt_signed_pct(growth)})" if growth is not None else "")
                )
                _add_fact(
                    facts,
                    fact_id="TIME-G02",
                    title="Registros del primer vs último año",
                    value=float(growth) if growth is not None else 0.0,
                    display_value=display,
                    unit="%",
                    category="actividad",
                    severity="info",
                    direction="neutral",
                    definition=(
                        "Comparación solo entre el primer y el último año con datos; "
                        "no se afirma una tendencia intermedia sin calcularla."
                    ),
                    evidence=f"count por año sobre '{roles.get('date')}'",
                    sample_size=len(dates),
                )

    categoric_column = _pick_categoric_column(work, roles)
    if categoric_column:
        counts = work[categoric_column].dropna().astype(str).value_counts()
        total = int(counts.sum())
        top3 = counts.head(3)
        display = ", ".join(f"{name} {_fmt_pct(int(n) / total)}" for name, n in top3.items())
        _add_fact(
            facts,
            fact_id="CAT-G01",
            title=f"Composición por '{categoric_column}'",
            value=float(int(top3.iloc[0]) / total),
            display_value=display,
            unit="%",
            category="composición",
            severity="info",
            direction="neutral",
            definition=(
                f"Top 3 valores de '{categoric_column}' por número de registros; el porcentaje es su "
                f"participación sobre {_fmt_count(total)} filas con valor."
            ),
            evidence=f"value_counts de '{categoric_column}'",
            sample_size=total,
        )

    metric_column = _pick_metric_column(work, roles)
    if metric_column:
        column_data = work[metric_column]
        if pd.api.types.is_numeric_dtype(column_data):
            valid = pd.to_numeric(column_data, errors="coerce").dropna()
        else:
            valid = _to_numeric(column_data).dropna()
        if len(valid):
            _add_fact(
                facts,
                fact_id="MET-G01",
                title=f"Promedio de '{metric_column}'",
                value=float(valid.mean()),
                display_value=_fmt_number(float(valid.mean())),
                unit=str(work[metric_column].name or metric_column),
                category="perfil",
                severity="info",
                direction="neutral",
                definition=(
                    f"Media aritmética de '{metric_column}' calculada con las "
                    f"{_fmt_count(len(valid))} filas con valor numérico."
                ),
                evidence=f"mean de '{metric_column}'",
                sample_size=len(valid),
            )
            _add_fact(
                facts,
                fact_id="MET-G02",
                title=f"Mediana de '{metric_column}'",
                value=float(valid.median()),
                display_value=_fmt_number(float(valid.median())),
                unit=str(work[metric_column].name or metric_column),
                category="perfil",
                severity="info",
                direction="neutral",
                definition=(
                    f"Valor central de '{metric_column}': la mitad de las filas está por debajo "
                    "y la otra mitad por encima. Menos sensible a valores extremos que el promedio."
                ),
                evidence=f"median de '{metric_column}'",
                sample_size=len(valid),
            )

    if not facts:
        _add_fact(
            facts,
            fact_id="GEN-01",
            title="Registros verificados",
            value=float(rows),
            display_value=f"{_fmt_count(rows)} filas sin columnas explotables para hallazgos",
            unit="filas",
            category="perfil",
            severity="info",
            direction="neutral",
            definition=(
                "El dataset solo permite verificar su tamaño: no hay fechas, categorías ni "
                "columnas numéricas utilizables. No se estima ningún otro hallazgo."
            ),
            evidence="len() del dataset tras limpieza",
            sample_size=rows,
        )
    return facts


def _render_narrative(
    facts: list[AuditFact],
    profile: dict[str, Any],
    analysis: dict[str, Any],
) -> str:
    by_id = {fact.id: fact for fact in facts}
    lines: list[str] = []
    source = profile.get("source_name") or "dataset"
    lines.append(f"## 🔎 Auditoría verificada: {source}")
    coverage = (
        f"**{_fmt_count(profile['rows'])} líneas** · "
        f"**{_fmt_count(profile['columns'])} columnas**"
    )
    if profile.get("orders") is not None:
        coverage += f" · **{_fmt_count(profile['orders'])} órdenes**"
    if profile.get("date_start") and profile.get("date_end"):
        coverage += f" · **{profile['date_start']} → {profile['date_end']}**"
    lines.append(coverage)
    lines.append(f"*Granularidad: {profile.get('grain', 'no determinada')}.*")
    lines.append("")

    sales = by_id.get("KPI-01")
    profit = by_id.get("KPI-02")
    margin = by_id.get("KPI-03")
    threshold = by_id.get("DISC-03")
    deep = by_id.get("DISC-04")
    deep_sales = by_id.get("DISC-05")
    last_profitable = by_id.get("DISC-06")
    extreme = by_id.get("DISC-07")
    negative_lines = by_id.get("LOSS-01")
    gross_loss = by_id.get("LOSS-02")
    negative_orders = by_id.get("LOSS-04")

    lines.append("### Diagnóstico")
    generic_peak = by_id.get("TIME-G01")
    generic_trend = by_id.get("TIME-G02")
    generic_composition = by_id.get("CAT-G01")
    generic_mean = by_id.get("MET-G01")
    generic_median = by_id.get("MET-G02")
    if sales and profit:
        headline = f"El dataset registra **{sales.display_value}** en ventas y **{profit.display_value}** de profit"
        if margin:
            headline += f", con un margen agregado de **{margin.display_value}**"
        headline += "."
        lines.append(headline)
    elif profit:
        lines.append(f"El dataset registra **{profit.display_value}** de profit, pero no hay una columna de ventas para calcular el margen.")
    elif sales:
        lines.append(f"El dataset registra **{sales.display_value}** en ventas, pero no hay una columna de profit para calcular rentabilidad.")
    elif facts:
        # P-59: hechos genéricos calculados de las columnas disponibles.
        lines.append(
            "El dataset no tiene columnas de ventas ni de profit. Los hallazgos verificables "
            "se calculan con las columnas disponibles: composición, actividad en el tiempo y "
            "estadísticos. No se estima ninguna métrica de negocio que el archivo no contenga."
        )
        if generic_peak:
            lines.append(f"El periodo con más registros es **{generic_peak.display_value}**.")
        if generic_trend:
            lines.append(f"Al comparar el primer y el último año con datos: **{generic_trend.display_value}**.")
        if generic_composition:
            composition_label = generic_composition.title.split("'", 1)[-1].rstrip("'")
            lines.append(
                f"Por **{composition_label}**, los valores más frecuentes son: {generic_composition.display_value}."
            )
        if generic_mean and generic_median:
            lines.append(
                f"La columna métrica detectada tiene promedio **{generic_mean.display_value}** "
                f"y mediana **{generic_median.display_value}**."
            )
    else:
        lines.append("No se detectaron columnas de ventas ni de profit; la auditoría se limita al perfil y la calidad del dataset.")

    if negative_lines and gross_loss:
        lines.append(
            f"La señal de pérdida no es el profit neto: hay **{negative_lines.display_value}** líneas con profit negativo "
            f"que suman una **pérdida bruta de {_fmt_money(abs(gross_loss.value))}**. "
            "Las líneas positivas compensan parte de esa pérdida, por eso no se debe presentar como fuga neta."
        )
    if negative_orders:
        lines.append(
            f"Al agrupar por orden, **{negative_orders.display_value}** órdenes terminan con profit neto negativo. "
            "Ese porcentaje no es el mismo que el de líneas negativas y no deben intercambiarse."
        )
    any_negative_orders = by_id.get("LOSS-06")
    if any_negative_orders:
        lines.append(
            f"Además, **{any_negative_orders.display_value}** órdenes tienen al menos una línea negativa; "
            "muchas siguen siendo rentables en conjunto. Es un tercer denominador distinto y no se debe usar como si fuera el neto."
        )
    if threshold and deep:
        lines.append(
            f"El descuento es el factor con mayor señal: **{threshold.display_value}** es el primer nivel que destruye margen "
            f"y el tramo ≥{threshold.display_value} aporta **{deep.display_value}**."
        )
        if deep_sales:
            lines.append(
                f"Ese tramo concentra **{deep_sales.display_value}** de las ventas, así que no es un residuo pequeño."
            )
        if last_profitable:
            lines.append(
                f"El último nivel que sigue siendo rentable es **{last_profitable.display_value}**; "
                "por encima de ahí el negocio necesita una razón explícita y una simulación de margen."
            )
    if extreme and extreme.value < 0:
        lines.append(
            f"El descuento extremo también tiene costo: el tramo ≥50% deja **{extreme.display_value}**."
        )

    for fact_id, sentence in (
        ("SEG-01", "La peor subcategoría por profit es"),
        ("SEG-02", "La categoría con menor margen es"),
        ("REG-01", "La región con menor margen es"),
    ):
        fact = by_id.get(fact_id)
        if fact:
            lines.append(f"{sentence} **{fact.title.split(': ', 1)[-1]}**, con **{fact.display_value}**.")
    gap = by_id.get("REG-02")
    if gap:
        lines.append(f"La brecha de margen entre regiones es **{gap.display_value}**.")
    discount_gap = by_id.get("REG-03")
    if discount_gap:
        lines.append(
            f"La brecha de líneas con descuento profundo es **{discount_gap.display_value}**; "
            "eso apunta a política comercial, no solo a mezcla de productos."
        )
    customer = by_id.get("CUST-01")
    if customer:
        lines.append(
            f"En clientes, **{customer.display_value}** terminan con pérdida. "
            "La pérdida de clientes es una suma de profits negativos netos, no el profit total del negocio."
        )
    concentration = by_id.get("CUST-02")
    if concentration:
        lines.append(
            f"Los 10 peores clientes concentran **{concentration.display_value}** de esa pérdida; "
            "es una lista corta para revisar, no una conclusión sobre todos los clientes."
        )
    time_sales = by_id.get("TIME-01")
    time_margin = by_id.get("TIME-02")
    if time_sales or time_margin:
        parts = []
        if time_sales:
            parts.append(f"ventas **{time_sales.display_value}**")
        if time_margin:
            parts.append(f"margen **{time_margin.display_value}**")
        lines.append(
            "En el tiempo, " + " y ".join(parts) +
            ". Se compara el primer y el último año; no se afirma una tendencia intermedia sin calcularla."
        )
    latest_margin = by_id.get("TIME-03")
    if latest_margin:
        lines.append(f"El último año cierra con **{latest_margin.display_value}**.")

    lines.append("")
    lines.append("### Hallazgos que sostienen el diagnóstico")
    shown = [fact for fact in facts if fact.id not in {"KPI-01", "KPI-02", "KPI-03"}]
    shown.sort(key=lambda fact: ({"alta": 0, "media": 1, "info": 2, "baja": 3}.get(fact.severity, 9), fact.id))
    for fact in shown[:12]:
        lines.append(f"- **{fact.title}:** {fact.display_value}. {fact.definition}")

    lines.append("")
    lines.append("### Qué haría")
    actions: list[str] = []
    if threshold and last_profitable:
        actions.append(
            f"Capar el descuento estándar en **{last_profitable.display_value}** y exigir aprobación para niveles superiores, "
            "empezando por el tramo ≥" + threshold.display_value + "."
        )
    if by_id.get("SEG-01"):
        actions.append(
            f"Revisar precio, costo y mezcla de **{by_id['SEG-01'].title.split(': ', 1)[-1]}**; "
            "no basta con subir el descuento ni con mirar solo las ventas."
        )
    if by_id.get("REG-01"):
        actions.append(
            f"Auditar la política comercial de **{by_id['REG-01'].title.split(': ', 1)[-1]}** y comparar su descuento profundo con la mejor región."
        )
    if by_id.get("CUST-01"):
        actions.append(
            "Revisar los 10 clientes con mayor pérdida y separar los que son estratégicos de los que destruyen margen de forma estructural."
        )
    if by_id.get("TIME-03"):
        actions.append(
            "Monitorear el margen del último año contra el año anterior antes de extrapolar una tendencia."
        )
    if not actions:
        if sales or profit:
            actions.append("Definir una métrica de rentabilidad y un dueño antes de sacar conclusiones de negocio.")
        else:
            actions.append(
                "Definir qué representa cada fila de este dataset y cuál es su métrica de negocio "
                "(casos, eventos, tasas, costos…), con un dueño, antes de traducir composición y "
                "actividad en decisiones. Las cifras de arriba están verificadas; las conclusiones "
                "de negocio requieren esa definición."
            )
    for index, action in enumerate(actions, start=1):
        lines.append(f"{index}. {action}")

    lines.append("")
    lines.append("### Cómo se calculó")
    lines.append(
        "Auditoría determinista con pandas. No se ejecutó código generado por un LLM y no se necesitó una API key. "
        "Cada tarjeta tiene un `id`, una definición y la evidencia del cálculo."
    )
    # P-59: sin ventas ni profit no se muestran las definiciones de retail;
    # solo las que aplican a los hechos genéricos realmente calculados.
    definitions = DEFINITIONS if (sales or profit) else GENERIC_DEFINITIONS
    for definition in definitions:
        lines.append(f"- **{definition['term']}:** {definition['definition']}")
    if profile.get("quality"):
        lines.append("")
        lines.append("**Calidad del dataset:** " + " ".join(profile["quality"]))
    return "\n".join(lines)


def _build_figure(
    df: pd.DataFrame,
    analysis: dict[str, Any],
    profile: dict[str, Any],
) -> Optional[go.Figure]:
    panels: list[tuple[str, Any]] = []

    discount_levels = analysis.get("discount_levels")
    if discount_levels is not None and not discount_levels.empty:
        panels.append(("discount", discount_levels))
    region = analysis.get("region")
    if region is not None and not region.empty:
        panels.append(("region", region))
    subcategory = analysis.get("subcategory")
    if subcategory is not None and not subcategory.empty:
        panels.append(("subcategory", subcategory))
    years = analysis.get("years")
    if years is not None and not years.empty:
        panels.append(("year", years))
    customers = analysis.get("top_loss")
    if customers is not None and not customers.empty and len(panels) < 4:
        panels.append(("customers", customers))

    if not panels:
        return None

    panel_count = len(panels)
    if panel_count == 1:
        rows, cols = 1, 1
    elif panel_count == 2:
        rows, cols = 1, 2
    else:
        rows, cols = 2, 2

    titles = {
        "discount": "Profit por nivel de descuento",
        "region": "Margen por región",
        "subcategory": "Profit por subcategoría",
        "year": "Profit por año",
        "customers": "Top 10 clientes por pérdida",
    }
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=[titles[kind] for kind, _ in panels],
        vertical_spacing=0.18 if rows > 1 else 0.0,
        horizontal_spacing=0.13,
    )

    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for index, (kind, data) in enumerate(panels):
        row, col = positions[index]
        if kind == "discount":
            labels = [f"{level * 100:.0f}%" for level in data["__discount_level"]]
            values = data["profit"].astype(float).tolist()
            colors = ["#ef4444" if value < 0 else "#22c55e" for value in values]
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    marker_color=colors,
                    text=[_fmt_money(value) for value in values],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="Descuento %{x}<br>Profit %{y:$,.0f}<extra></extra>",
                ),
                row=row,
                col=col,
            )
            fig.update_xaxes(title_text="Descuento", row=row, col=col)
            fig.update_yaxes(title_text="Profit (USD)", row=row, col=col)
        elif kind == "region":
            labels = data[profile["roles"].get("region") or data.columns[0]].astype(str).tolist()
            values = (data["margin"].astype(float) * 100).tolist()
            colors = ["#ef4444" if value < 0 else "#f59e0b" if value < 8 else "#22c55e" for value in values]
            fig.add_trace(
                go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color=colors,
                    text=[f"{value:.1f}%" for value in values],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}<br>Margen %{x:.1f}%<extra></extra>",
                ),
                row=row,
                col=col,
            )
            fig.update_xaxes(title_text="Margen (%)", row=row, col=col)
        elif kind == "subcategory":
            dim = profile["roles"].get("subcategory") or data.columns[0]
            worst = data.head(8).sort_values("profit", ascending=True)
            labels = worst[dim].astype(str).tolist()
            values = worst["profit"].astype(float).tolist()
            colors = ["#ef4444" if value < 0 else "#22c55e" for value in values]
            fig.add_trace(
                go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color=colors,
                    text=[_fmt_money(value) for value in values],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}<br>Profit %{x:$,.0f}<extra></extra>",
                ),
                row=row,
                col=col,
            )
            fig.update_xaxes(title_text="Profit (USD)", row=row, col=col)
        elif kind == "year":
            labels = [str(int(year)) for year in data["__year"].tolist()]
            values = data["profit"].astype(float).tolist()
            margins = data["margin"].astype(float).tolist()
            colors = ["#ef4444" if value < 0 else "#2dd4bf" for value in values]
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    marker_color=colors,
                    text=[_fmt_money(value) for value in values],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=[f"{margin * 100:.1f}%" for margin in margins],
                    hovertemplate="Año %{x}<br>Profit %{y:$,.0f}<br>Margen %{customdata}<extra></extra>",
                ),
                row=row,
                col=col,
            )
            fig.update_yaxes(title_text="Profit (USD)", row=row, col=col)
        elif kind == "customers":
            dim = profile["roles"].get("customer") or data.columns[0]
            worst = data.head(10).sort_values("profit", ascending=True)
            labels = [str(value)[:22] for value in worst[dim].tolist()]
            values = worst["profit"].astype(float).tolist()
            fig.add_trace(
                go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color="#ef4444",
                    text=[_fmt_money(value) for value in values],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}<br>Profit %{x:$,.0f}<extra></extra>",
                ),
                row=row,
                col=col,
            )
            fig.update_xaxes(title_text="Profit (USD)", row=row, col=col)

    fig.update_layout(
        height=620 if rows > 1 else 360,
        showlegend=False,
        margin={"l": 55, "r": 20, "t": 45, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "size": 10, "color": "#a1a1aa"},
        bargap=0.25,
    )
    fig.update_annotations(font_size=11, font_color="#d4d4d8")
    fig.update_xaxes(showgrid=False, zerolinecolor="rgba(148,163,184,0.25)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.14)", zerolinecolor="rgba(148,163,184,0.25)")
    return fig


def build_audit(
    data: Any,
    primary_source_name: Optional[str] = None,
    source_name: Optional[str] = None,
) -> dict[str, Any]:
    """Calcula la auditoría y devuelve un paquete serializable (excepto la figura Plotly)."""
    df, detected_name = _select_dataframe(data, primary_source_name)
    work, roles, profile, quality = _prepare_frame(df, primary_source_name)
    if source_name:
        profile["source_name"] = source_name
    else:
        profile["source_name"] = detected_name

    if not roles.get("sales") and not roles.get("profit"):
        # Sin ventas ni profit no se calcula nada de retail (P-59): en lugar de
        # devolver solo perfil, se calculan hechos genéricos verificables de
        # las columnas disponibles (composición, actividad temporal,
        # estadísticos). Si no hay nada explotable, el perfil sigue siendo
        # honesto sobre lo que falta.
        analysis = {
            "available": False,
            "threshold": None,
            "last_profitable": None,
            "levels": None,
            "deep_loss": None,
            "deep_sales_share": None,
            "deep_profit_share": None,
            "discount_levels": None,
            "subcategory": None,
            "category": None,
            "region": None,
            "customers": None,
            "top_loss": None,
            "years": None,
        }
        facts: list[AuditFact] = _generic_facts(work, roles, profile)
        narrative = _render_narrative(facts, profile, analysis)
        return {
            "analysis": narrative,
            "figure": None,
            "insights": [asdict(fact) for fact in facts],
            "profile": profile,
            "definitions": GENERIC_DEFINITIONS,
            "methodology": _methodology(profile),
            "source_name": profile["source_name"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    facts: list[AuditFact] = []
    total_sales = float(work["__sales"].sum()) if "__sales" in work else None
    total_profit = float(work["__profit"].sum()) if "__profit" in work else None
    if total_sales is not None:
        _add_fact(
            facts,
            fact_id="KPI-01",
            title="Ventas totales",
            value=total_sales,
            display_value=_fmt_money(total_sales),
            unit="USD",
            category="perfil",
            severity="info",
            direction="positive" if total_sales >= 0 else "negative",
            definition="Suma de la columna de ventas en todas las líneas.",
            evidence=f"sum({roles.get('sales')})",
            sample_size=len(work),
        )
    if total_profit is not None:
        _add_fact(
            facts,
            fact_id="KPI-02",
            title="Profit neto",
            value=total_profit,
            display_value=_fmt_money(total_profit),
            unit="USD",
            category="perfil",
            severity="info",
            direction="positive" if total_profit >= 0 else "negative",
            definition="Suma de todos los profits, positivos y negativos. Es la ganancia o pérdida final del periodo.",
            evidence=f"sum({roles.get('profit')})",
            sample_size=len(work),
        )
    if total_sales is not None and total_profit is not None:
        overall_margin = _margin(total_profit, total_sales)
        if overall_margin is not None:
            _add_fact(
                facts,
                fact_id="KPI-03",
                title="Margen agregado",
                value=overall_margin,
                display_value=_fmt_pct(overall_margin),
                unit="%",
                category="perfil",
                severity="info",
                direction="positive" if overall_margin >= 0 else "negative",
                definition="Profit neto dividido entre ventas totales. No es el promedio de márgenes por línea.",
                evidence="sum(profit) / sum(sales)",
                sample_size=len(work),
            )

    analysis: dict[str, Any] = {
        "available": False,
        "threshold": None,
        "last_profitable": None,
        "levels": None,
        "deep_loss": None,
        "deep_sales_share": None,
        "deep_profit_share": None,
        "discount_levels": None,
        "subcategory": None,
        "category": None,
        "region": None,
        "customers": None,
        "top_loss": None,
        "years": None,
    }
    if roles.get("discount") and roles.get("profit"):
        discount_analysis = _discount_analysis(work, facts)
        analysis.update(discount_analysis)
        analysis["discount_levels"] = discount_analysis.get("levels")

    _loss_facts(work, facts)
    detected_threshold = analysis.get("threshold")
    deep_threshold = float(detected_threshold) if detected_threshold is not None else 0.5
    segment_analysis = _segment_facts(work, roles, facts, deep_threshold=deep_threshold)
    analysis.update(segment_analysis)
    customer_analysis = _customer_facts(work, roles, facts)
    analysis.update(customer_analysis)
    time_analysis = _time_facts(work, roles, facts)
    analysis.update(time_analysis)

    narrative = _render_narrative(facts, profile, analysis)
    figure = _build_figure(work, analysis, profile)
    return {
        "analysis": narrative,
        "figure": figure,
        "insights": [asdict(fact) for fact in facts],
        "profile": profile,
        "definitions": DEFINITIONS,
        "methodology": _methodology(profile),
        "source_name": profile["source_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _methodology(profile: dict[str, Any]) -> list[str]:
    return [
        "Auditoría determinista con pandas; no se ejecuta código generado por el LLM.",
        "Los roles se detectan por nombre de columna; si no hay coincidencia, la métrica se marca como no medible.",
        "Las líneas son filas; las órdenes solo se calculan si existe un identificador de orden.",
        "El margen es profit / ventas agregados, no el promedio de márgenes por línea.",
        "La pérdida bruta suma solo profits negativos; el profit neto suma profits positivos y negativos.",
        "Los grupos con poco volumen se excluyen para evitar conclusiones de dos o tres filas.",
        f"El umbral de descuento se calcula por nivel exacto y exige al menos {max(10, int(profile['rows'] * 0.001))} líneas.",
        "La narrativa se renderiza desde los hechos con id, definición y evidencia; los números no se inventan.",
    ]
