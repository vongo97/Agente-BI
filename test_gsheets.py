import sys
import os

# Asegurarse de que el directorio server está en el path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from src.connectors.data_connectors import load_gsheets_data

def test_google_sheets():
    # URL pública de ejemplo (Google Sheets API developer example)
    url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
    print(f"Probando conexión con: {url}")
    
    try:
        df = load_gsheets_data(url)
        if df is not None:
            print(f"¡ÉXITO! Se cargaron {len(df)} filas y {len(df.columns)} columnas.")
            print("\nPrimeras 2 filas:")
            print(df.head(2).to_string())
        else:
            print("ERROR: La función devolvió None.")
    except Exception as e:
        print(f"ERROR DURANTE LA PRUEBA: {str(e)}")

if __name__ == "__main__":
    test_google_sheets()
