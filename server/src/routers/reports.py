import logging
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from src.database import get_db, DataSource
from src.utils.common import check_authorization, get_user_data, get_authenticated_user, json_serializable
from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reports"])


@router.post("/report/kpi-summary")
@limiter.limit("10/minute")
@limiter.limit("60/hour")
async def kpi_summary(
    request: Request,
    data_source_id: int = Form(...),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)

    source = db.query(DataSource).filter(
        DataSource.id == data_source_id,
        DataSource.user_id == authenticated_user
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Recurso no encontrado o sin acceso")

    from src.utils.common import ensure_user_session
    session_data = ensure_user_session(authenticated_user, db)
    if not session_data or "data" not in session_data or not session_data["data"]:
        raise HTTPException(status_code=400, detail="No hay datos cargados en la sesión")

    safe_name = "".join([c if c.isalnum() else "_" for c in source.name.split('.')[0]])
    df = session_data["data"].get(safe_name)
    if df is None or not isinstance(df, pd.DataFrame):
        for _name, frame in session_data["data"].items():
            if isinstance(frame, pd.DataFrame):
                df = frame
                break
    if df is None or not isinstance(df, pd.DataFrame):
        raise HTTPException(status_code=400, detail="No se pudo cargar el DataFrame")

    num_rows = len(df)
    num_cols = len(df.columns)
    total_cells = num_rows * num_cols

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    non_null_count = df.notnull().sum().sum()
    completeness = round((non_null_count / total_cells) * 100, 2) if total_cells > 0 else 100.0

    outliers = []
    for col in numeric_cols:
        col_data = df[col].dropna()
        if len(col_data) < 5:
            continue
        mean = col_data.mean()
        std = col_data.std()
        if std == 0 or pd.isna(std):
            continue
        z_scores = (col_data - mean) / std
        outlier_mask = z_scores.abs() > 3
        for idx in col_data[outlier_mask].index:
            z = float(z_scores.loc[idx])
            outliers.append({
                "columna": col,
                "valor": float(col_data.loc[idx]),
                "z_score": round(z, 2),
                "media": round(float(mean), 2),
                "severidad": "Alta" if abs(z) > 5 else ("Media" if abs(z) > 4 else "Baja")
            })
    outliers.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    outliers = outliers[:10]

    correlations = []
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.7 and not pd.isna(r):
                    correlations.append({
                        "columna_a": numeric_cols[i],
                        "columna_b": numeric_cols[j],
                        "r": round(float(r), 4)
                    })
        correlations.sort(key=lambda x: abs(x["r"]), reverse=True)

    top_niche = "N/A"
    if categorical_cols:
        for cat_col in categorical_cols:
            freq = df[cat_col].dropna().value_counts()
            if not freq.empty:
                top_niche = f"{freq.index[0]} ({freq.iloc[0]} ocurrencias)"
                break

    saturation_index = round((len(numeric_cols) / num_cols) * 100, 1) if num_cols > 0 else 0.0

    outlier_penalty = len(outliers) * 0.5
    confidence = round(max(0, min(100, completeness - outlier_penalty)), 1)

    result = {
        "dataset": {
            "nombre": source.name,
            "filas": num_rows,
            "columnas": num_cols
        },
        "columnas": {
            "numericas": len(numeric_cols),
            "categoricas": len(categorical_cols),
            "lista_numericas": numeric_cols[:15],
            "lista_categoricas": categorical_cols[:15]
        },
        "saturacion": saturation_index,
        "nicho_top": top_niche,
        "confianza": confidence,
        "completitud": completeness,
        "anomalias": outliers,
        "correlaciones_fuertes": correlations[:10]
    }

    return json_serializable(result)
