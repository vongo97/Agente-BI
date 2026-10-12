# -*- coding: utf-8 -*-
"""
Generador de archivos de prueba/estrés para Vektra BI.

Crea 5 categorías de archivos dentro de `datasets_vektra/stress/`:
  1. GRANDES      - Archivos pesados para probar rendimiento y memoria.
  2. SUCIOS       - Nulos, tipos mixtos, duplicados, encoding raro, fechas inválidas.
  3. NORMALES     - Pequeños, limpios y realistas (flujo básico).
  4. LÍMITES      - Archivos vacíos, nombres de columna maliciosos, celdas gigantes.
  5. SQL          - Dump SQLite válido con datos masivos + dump malformado.

Uso:
    .\\venv\\Scripts\\python.exe generate_stress_files.py
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets_vektra", "stress")
random.seed(42)
np.random.seed(42)

os.makedirs(BASE_DIR, exist_ok=True)


def out(name: str) -> str:
    return os.path.join(BASE_DIR, name)


# ---------------------------------------------------------------------------
# 1. GRANDES
# ---------------------------------------------------------------------------
def gen_large_csv():
    print("[1/9] Generando ventas_1M_filas.csv (1,000,000 filas)...")
    n = 1_000_000
    start = datetime(2023, 1, 1)
    df = pd.DataFrame({
        "order_id": [f"ORD-{i:08d}" for i in range(n)],
        "fecha": [(start + timedelta(minutes=int(m))).strftime("%Y-%m-%d %H:%M")
                  for m in np.random.randint(0, 1_500_000, n)],
        "cliente_id": np.random.randint(1, 50_000, n),
        "categoria": np.random.choice(["Electrónica", "Hogar", "Moda", "Deporte", "Alimentación"], n),
        "region": np.random.choice(["Norte", "Sur", "Centro", "Este", "Oeste"], n),
        "unidades": np.random.randint(1, 20, n),
        "precio_unitario": np.round(np.random.lognormal(3.5, 0.9, n), 2),
        "descuento_pct": np.round(np.random.uniform(0, 0.5, n), 3),
        "envio_gratis": np.random.choice([True, False], n, p=[0.2, 0.8]),
    })
    df["total"] = (df["unidades"] * df["precio_unitario"] * (1 - df["descuento_pct"])).round(2)
    df.to_csv(out("grande_ventas_1M_filas.csv"), index=False)


def gen_large_excel():
    print("[2/9] Generando metricas_300k_filas.xlsx (puede tardar 1-3 min)...")
    n = 300_000
    start = datetime(2024, 1, 1)
    df = pd.DataFrame({
        "id": np.arange(n),
        "fecha": [(start + timedelta(hours=int(h))).strftime("%Y-%m-%d") for h in np.random.randint(0, 17_520, n)],
        "servicio": np.random.choice(["web", "mobile", "api_web", "api_mobile", "etl"], n),
        "latencia_ms": np.round(np.random.gamma(2.0, 40, n), 1),
        "errores": np.random.poisson(0.4, n),
        "usuarios_activos": np.random.randint(0, 20_000, n),
        "region": np.random.choice(["EU", "US", "LATAM", "APAC"], n),
    })
    df.to_excel(out("grande_metricas_300k_filas.xlsx"), index=False, sheet_name="metricas")


# ---------------------------------------------------------------------------
# 2. SUCIOS
# ---------------------------------------------------------------------------
def gen_dirty_csv():
    print("[3/9] Generando sucio_datos_rotos.csv (encoding latin-1, nulos, tipos mixtos)...")
    rows = []
    for i in range(5_000):
        precio = random.choice(["12.5", "12,5", "gratis", "", "NaN", "9.99", "null"])
        fecha = random.choice(["2025-01-15", "15/01/2025", "2025-13-40", "ayer", "", "0000-00-00"])
        unidad = random.choice(["1", "2", "-3", "dos", "", "999999999999999999999"])
        ciudad = random.choice(["Madrid", "Bogotá", "São Paulo", "München", "Århus", ""])
        rows.append([i, ciudad, fecha, precio, unidad])
    # Duplicados
    rows += random.sample(rows, 300)

    # Escritura manual con encoding latin-1 para romper parsers que asumen UTF-8
    with open(out("sucio_datos_rotos.csv"), "w", encoding="latin-1", newline="") as f:
        f.write("id,ciudad,fecha,precio,unidades\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")
        # Filas con número de columnas incorrecto y comillas sin cerrar
        f.write('9999,"Ciudad sin cerrar,2025-01-01,broken\n')
        f.write("9998,Madrid,2025-01-02,10.0,3,columna_extra_no_esperada\n")


def gen_dirty_excel():
    print("[4/9] Generando sucio_multihoja.xlsx (tipos mixtos, hojas irregulares)...")
    df1 = pd.DataFrame({
        "monto": (["100.5", "s/n", 200, None, "1.000,99", -50, 300.75, "", "N/A"] * 112)[:1000],
        "fecha": pd.Series(["2025-01-01", "31/02/2025", None, datetime.now(), "texto"] * 200),
        "activo": [True, "True", "si", 1, None] * 200,
    })
    # Segunda hoja totalmente vacía salvo título, tercera con solo strings
    df2 = pd.DataFrame({"solo_titulo": []})
    df3 = pd.DataFrame({"a": ["x", "y", "z"], "b": ["1", "2", "3"]})
    with pd.ExcelWriter(out("sucio_multihoja.xlsx")) as xw:
        df1.to_excel(xw, sheet_name="montos", index=False)
        df2.to_excel(xw, sheet_name="vacia", index=False)
        df3.to_excel(xw, sheet_name="texto", index=False)


# ---------------------------------------------------------------------------
# 3. NORMALES PEQUEÑOS
# ---------------------------------------------------------------------------
def gen_small_clean_csv():
    print("[5/9] Generando ventas_mensuales_2025.csv (limpio, 120 filas)...")
    meses = pd.date_range("2025-01-01", periods=12, freq="MS")
    rows = []
    for m in meses:
        for cat in ["Electrónica", "Hogar", "Moda", "Deporte", "Alimentación",
                    "Juguetes", "Libros", "Belleza", "Mascotas", "Jardín"]:
            rows.append({
                "mes": m.strftime("%Y-%m"),
                "categoria": cat,
                "ventas": round(random.uniform(5_000, 60_000), 2),
                "unidades": random.randint(100, 2_000),
                "devoluciones": random.randint(0, 40),
            })
    pd.DataFrame(rows).to_csv(out("normal_ventas_mensuales_2025.csv"), index=False)


def gen_small_clean_excel():
    print("[6/9] Generando kpis_trimestrales.xlsx (limpio, múltiples hojas)...")
    df_resumen = pd.DataFrame({
        "trimestre": ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"],
        "ingresos": [125_000, 148_000, 162_500, 190_200],
        "gastos": [98_000, 105_000, 110_000, 121_300],
        "clientes_nuevos": [320, 410, 380, 520],
    })
    df_resumen["beneficio"] = df_resumen["ingresos"] - df_resumen["gastos"]
    df_canales = pd.DataFrame({
        "canal": ["Orgánico", "Pagado", "Referido", "Email"],
        "leads": [1200, 3400, 640, 980],
        "conversion_pct": [3.2, 2.1, 5.6, 8.4],
    })
    with pd.ExcelWriter(out("normal_kpis_trimestrales.xlsx")) as xw:
        df_resumen.to_excel(xw, sheet_name="resumen", index=False)
        df_canales.to_excel(xw, sheet_name="canales", index=False)


# ---------------------------------------------------------------------------
# 4. LÍMITES / MALICIOSOS
# ---------------------------------------------------------------------------
def gen_edge_files():
    print("[7/9] Generando archivos de límites (vacío, headers maliciosos, celda gigante)...")
    # Archivo totalmente vacío
    open(out("borde_archivo_vacio.csv"), "wb").close()

    # Solo encabezados, sin filas
    with open(out("borde_solo_encabezados.csv"), "w", encoding="utf-8") as f:
        f.write("id,nombre,valor\n")

    # SQL dump de SQLite válido con ~100k filas
    db_path = out("sql_ecommerce_valido.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE clientes (id INTEGER PRIMARY KEY, nombre TEXT, email TEXT, pais TEXT);
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY, cliente_id INTEGER, fecha TEXT,
            total REAL, estado TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        );
    """)
    paises = ["ES", "MX", "CO", "AR", "CL", "PE", "US"]
    cur.executemany(
        "INSERT INTO clientes VALUES (?, ?, ?, ?)",
        [(i, f"Cliente {i}", f"cliente{i}@mail.com", random.choice(paises)) for i in range(1, 5_001)],
    )
    cur.executemany(
        "INSERT INTO pedidos VALUES (?, ?, ?, ?, ?)",
        [(i, random.randint(1, 5_000),
          (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d"),
          round(random.uniform(10, 2_000), 2),
          random.choice(["completado", "pendiente", "cancelado", "devuelto"]))
         for i in range(1, 100_001)],
    )
    con.commit()
    con.close()

    # También un .sql de texto (dump tipo mysqldump)
    with open(out("sql_ecommerce_dump.sql"), "w", encoding="utf-8") as f:
        f.write("-- Dump de prueba\n")
        f.write("CREATE TABLE productos (id INT PRIMARY KEY, nombre VARCHAR(255), precio DECIMAL(10,2));\n")
        f.write("INSERT INTO productos (id, nombre, precio) VALUES\n")
        f.write(",\n".join(f"({i}, 'Producto {i}', {round(random.uniform(1, 999), 2)})" for i in range(1, 5001)))
        f.write(";\n")

    # SQL malformado / con errores de sintaxis
    with open(out("sql_malformado.sql"), "w", encoding="utf-8") as f:
        f.write("CREATE TABEL usuarios (id INTERGER, nombre TEXT)\n")
        f.write("INSER INTO usuarios VALUES (1, 'Ana');\n")
        f.write("SELECT * FROM tabla_inexistente;\n")


def gen_malicious_csvs():
    print("[8/9] Generando CSVs maliciosos (headers raros, celda gigante, muchas columnas)...")
    # Encabezados con emojis, SQL injection-like y duplicados
    with open(out("borde_headers_maliciosos.csv"), "w", encoding="utf-8") as f:
        f.write("id,nombre 😀,id'; DROP TABLE users;--,id,valor\n")
        for i in range(200):
            f.write(f"{i},usuario_{i},{i},{i},{round(random.uniform(0, 100), 2)}\n")

    # Una celda de texto enorme (1 MB) para probar límites de celda
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "texto_gigante": ["A" * 1_000_000, "normal", "".join("xyz\n" for _ in range(1000))],
    })
    df.to_csv(out("borde_celda_gigante.csv"), index=False)

    # Muchas columnas (2.000 columnas)
    ncols = 2_000
    cols = {f"col_{i}": np.random.randint(0, 100, 50) for i in range(ncols)}
    pd.DataFrame(cols).to_csv(out("borde_muchas_columnas.csv"), index=False)


if __name__ == "__main__":
    print(f"Generando archivos de estrés en: {BASE_DIR}\n")
    gen_large_csv()
    gen_large_excel()
    gen_dirty_csv()
    gen_dirty_excel()
    gen_small_clean_csv()
    gen_small_clean_excel()
    gen_edge_files()
    gen_malicious_csvs()
    print("\n[9/9] OK - Todos los archivos generados correctamente.")
