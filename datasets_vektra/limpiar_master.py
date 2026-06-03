import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
print("Iniciando limpieza del dataset maestro...")

# 1. Cargar el dataset con el encoding correcto
df = pd.read_csv('08_empresas_supersociedades.csv', encoding='latin-1')

# 2. Renombrar columnas para eliminar caracteres extraños y hacerlas claras
df.columns = [
    'NIT', 'RAZON_SOCIAL', 'SUPERVISOR', 'REGION', 'DEPARTAMENTO',
    'CIUDAD', 'CIIU', 'MACROSECTOR', 'INGRESOS_OP', 'GANANCIA',
    'TOTAL_ACTIVOS', 'TOTAL_PASIVOS', 'TOTAL_PATRIMONIO', 'ANO_CORTE'
]

# 3. Función para limpiar dinero (quitar $, comas y pasar a número)
def limpiar_dinero(val):
    try:
        return float(str(val).replace('$', '').replace(',', '').strip())
    except:
        return 0.0

print("Limpiando columnas financieras...")
for col in ['INGRESOS_OP', 'GANANCIA', 'TOTAL_ACTIVOS', 'TOTAL_PASIVOS', 'TOTAL_PATRIMONIO']:
    df[col] = df[col].apply(limpiar_dinero)

# 4. Filtrar para dejar solo el año más reciente de cada empresa (NIT)
print("Eliminando registros de años anteriores...")
df_latest = df.sort_values('ANO_CORTE', ascending=False).drop_duplicates(subset='NIT', keep='first')

# 5. Exportar el Master Limpio
salida_csv = '10_master_limpio_supersociedades.csv'
df_latest.to_csv(salida_csv, index=False, encoding='utf-8-sig')

print(f"\n¡Limpieza exitosa!")
print(f"Total de empresas únicas consolidadas: {len(df_latest)}")
print(f"Archivo generado: {salida_csv}")
