import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
print("Generando datos para IDEA 3 (El poder silencioso de las regiones)...")

# Cargar master limpio
df = pd.read_csv('10_master_limpio_supersociedades.csv')

# Excluir los 3 gigantes
excluir = ['BOGOTA D.C.', 'ANTIOQUIA', 'VALLE']
df_regiones = df[~df['DEPARTAMENTO'].isin(excluir)].copy()

# ==========================================
# PREGUNTA 1: Top 5 Departamentos
# ==========================================
p1 = df_regiones.groupby('DEPARTAMENTO').agg(
    Cantidad_Empresas=('NIT', 'count'),
    Suma_Ingresos=('INGRESOS_OP', 'sum')
).reset_index().sort_values('Suma_Ingresos', ascending=False).head(5)
p1.index = range(1, 6)
p1.index.name = 'Posicion'
p1.to_csv('11_P1_regiones_top5_departamentos.csv', encoding='utf-8-sig')
print("\n--- P1: Top 5 Departamentos ---")
print(p1)

# ==========================================
# PREGUNTA 2: Top 3 Municipios Imán
# ==========================================
top_deptos = p1['DEPARTAMENTO'].tolist()
df_top_deptos = df_regiones[df_regiones['DEPARTAMENTO'].isin(top_deptos)]

p2 = df_top_deptos.groupby(['CIUDAD', 'DEPARTAMENTO']).agg(
    Suma_Ingresos=('INGRESOS_OP', 'sum')
).reset_index().sort_values('Suma_Ingresos', ascending=False).head(3)
p2.index = range(1, 4)
p2.index.name = 'Posicion'
p2.to_csv('11_P2_regiones_top3_ciudades.csv', encoding='utf-8-sig')
print("\n--- P2: Top 3 Municipios Imán ---")
print(p2)

# ==========================================
# PREGUNTA 3: Motores Económicos (Macrosectores)
# ==========================================
top_ciudades = p2['CIUDAD'].tolist()
df_top_ciudades = df_top_deptos[df_top_deptos['CIUDAD'].isin(top_ciudades)]

p3 = df_top_ciudades.groupby(['CIUDAD', 'MACROSECTOR']).agg(
    Suma_Ingresos=('INGRESOS_OP', 'sum'),
    Cantidad_Empresas=('NIT', 'count')
).reset_index().sort_values(['CIUDAD', 'Suma_Ingresos'], ascending=[True, False])

p3.to_csv('11_P3_regiones_macrosectores.csv', index=False, encoding='utf-8-sig')
print("\n--- P3: Motores por Macrosector ---")
print(p3)

print("\nArchivos generados con éxito.")
