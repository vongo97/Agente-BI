import pandas as pd
import sys
from io import StringIO
import os

# Simulación de la lógica de data_connectors.py
def test_encoding():
    print("--- Probando soporte de múltiples encodings ---")
    test_file = "test_encoding.csv"
    try:
        # Crear un archivo con encoding latin-1 (byte 0x99 falla en utf-8)
        # 0x99 en Windows-1252 o similar suele causar problemas
        with open(test_file, "wb") as f:
            f.write(b"Categor\xed\xad\xad,Valor\nFinanzas,100\n")
        
        # Intentar cargar
        encodings = ['utf-8', 'latin-1', 'cp1252']
        success = False
        for enc in encodings:
            try:
                df = pd.read_csv(test_file, encoding=enc)
                print(f"Éxito leyendo con {enc}")
                success = True
                break
            except Exception as e:
                print(f"Fallo con {enc}: {e}")
        
        if success:
            print("✅ Prueba de encoding SUPERADA")
        else:
            print("❌ Prueba de encoding FALLIDA")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

# Simulación de la lógica de bi_analyst.py
def test_scope_and_exec():
    print("\n--- Probando scope de variables en exec() ---")
    code_to_run = """
def mi_funcion_interna():
    return pd.Series([1, 2, 3]).sum()

print(f'Resultado suma: {mi_funcion_interna()}')
"""
    data_context = pd.DataFrame({'a': [1,2,3]})
    var_name = "df"
    
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    # Namespace corregido
    exec_globals = {var_name: data_context, 'pd': pd}
    
    try:
        # Usar el mismo dict para globals y locals
        exec(code_to_run, exec_globals, exec_globals)
        output = redirected_output.getvalue().strip()
        print(f"Salida capturada: {output}", file=old_stdout)
        if "Resultado suma: 6" in output:
            print("✅ Prueba de scope SUPERADA", file=old_stdout)
        else:
            print("❌ Prueba de scope FALLIDA", file=old_stdout)
    except Exception as e:
        print(f"❌ Prueba de scope FALLIDA con error: {e}", file=old_stdout)
    finally:
        sys.stdout = old_stdout

if __name__ == "__main__":
    test_encoding()
    test_scope_and_exec()
