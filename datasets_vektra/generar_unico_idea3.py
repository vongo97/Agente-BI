import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Cargar master limpio
df = pd.read_csv('10_master_limpio_supersociedades.csv')

# Excluir los 3 gigantes
excluir = ['BOGOTA D.C.', 'ANTIOQUIA', 'VALLE']
df_regiones = df[~df['DEPARTAMENTO'].isin(excluir)].copy()

# Encontrar el Top 5 Departamentos reales
top5_deptos = df_regiones.groupby('DEPARTAMENTO')['INGRESOS_OP'].sum().nlargest(5).index.tolist()

# Filtrar solo la información de esos 5 departamentos ganadores
df_top5 = df_regiones[df_regiones['DEPARTAMENTO'].isin(top5_deptos)]

# Agrupar TODO en un solo nivel de detalle: Departamento -> Ciudad -> Sector
dataset_unico = df_top5.groupby(['DEPARTAMENTO', 'CIUDAD', 'MACROSECTOR']).agg(
    Suma_Ingresos_Billones=('INGRESOS_OP', 'sum'),
    Cantidad_Empresas=('NIT', 'count')
).reset_index()

# Ordenar de mayor a menor para que el LLM lo lea súper fácil
dataset_unico = dataset_unico.sort_values(by=['DEPARTAMENTO', 'Suma_Ingresos_Billones'], ascending=[True, False])

# Guardar en UN SOLO ARCHIVO
archivo_final = '12_dataset_unico_idea3.csv'
dataset_unico.to_csv(archivo_final, index=False, encoding='utf-8-sig')

print(f"¡Listo! Archivo {archivo_final} generado con {len(dataset_unico)} filas.")
