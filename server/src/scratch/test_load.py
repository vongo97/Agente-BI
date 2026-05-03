import pandas as pd
import os

files = [
    r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\#1- Tasa de cresimiento.csv",
    r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\#1-inflacion.csv"
]

for f in files:
    print(f"\n--- Analizando: {os.path.basename(f)} ---")
    try:
        # Simular carga con punto y coma
        df = pd.read_csv(f, sep=';', decimal=',', encoding='utf-8')
        print(f"Columnas detectadas: {df.columns.tolist()}")
        print(f"Primeras 2 filas:\n{df.head(2)}")
        print(f"Tipos de datos:\n{df.dtypes}")
    except Exception as e:
        print(f"Error cargando con UTF-8: {e}")
        try:
            df = pd.read_csv(f, sep=';', decimal=',', encoding='latin-1')
            print(f"EXITO con Latin-1. Columnas: {df.columns.tolist()}")
        except Exception as e2:
            print(f"Error crítico: {e2}")
