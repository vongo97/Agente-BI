import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Cargar CSV
df = pd.read_csv('08_empresas_supersociedades.csv', encoding='latin-1')
df.columns = ['NIT', 'RAZON_SOCIAL', 'SUPERVISOR', 'REGION', 'DEPARTAMENTO',
              'CIUDAD', 'CIIU', 'MACROSECTOR', 'INGRESOS_OP', 'GANANCIA',
              'TOTAL_ACTIVOS', 'TOTAL_PASIVOS', 'TOTAL_PATRIMONIO', 'ANO_CORTE']

def limpiar(val):
    try:
        return float(str(val).replace('$','').replace(',','').strip())
    except:
        return 0.0

for col in ['INGRESOS_OP','GANANCIA','TOTAL_ACTIVOS','TOTAL_PASIVOS','TOTAL_PATRIMONIO']:
    df[col+'_NUM'] = df[col].apply(limpiar)

# -------------------------------------------------------
# DATASET 1: Top 10 Comercio por Patrimonio (año más reciente por empresa)
# -------------------------------------------------------
comercio = df[df['MACROSECTOR'].str.upper() == 'COMERCIO'].copy()
# Tomar solo el año más reciente por empresa (NIT)
comercio_latest = comercio.sort_values('ANO_CORTE', ascending=False).drop_duplicates(subset='NIT', keep='first')
top10_patrimonio = comercio_latest.sort_values('TOTAL_PATRIMONIO_NUM', ascending=False).head(10).reset_index(drop=True)
top10_patrimonio.index = range(1,11)
top10_patrimonio.index.name = 'Posicion'
exportar1 = top10_patrimonio[['RAZON_SOCIAL','CIUDAD','DEPARTAMENTO','TOTAL_PATRIMONIO','INGRESOS_OP','ANO_CORTE']].copy()
exportar1.columns = ['Empresa','Ciudad','Departamento','Total Patrimonio','Ingresos Operacionales','Año de Corte']
exportar1.to_csv('09_P1_top10_comercio_patrimonio.csv', encoding='utf-8-sig')
print("=== PREGUNTA 1: Top 10 Comercio por Patrimonio ===")
print(exportar1.to_string())

# -------------------------------------------------------
# DATASET 2: Salud financiera (endeudamiento) de esas mismas 10 empresas
# -------------------------------------------------------
top10_patrimonio['ENDEUDAMIENTO'] = (top10_patrimonio['TOTAL_PASIVOS_NUM'] / top10_patrimonio['TOTAL_ACTIVOS_NUM']).round(2)

def categoria(r):
    if r < 0.40: return 'Solida'
    elif r <= 0.70: return 'Alerta'
    else: return 'Critica'

top10_patrimonio['CATEGORIA_SALUD'] = top10_patrimonio['ENDEUDAMIENTO'].apply(categoria)
exportar2 = top10_patrimonio[['RAZON_SOCIAL','CIUDAD','TOTAL_PATRIMONIO','TOTAL_PASIVOS','TOTAL_ACTIVOS','ENDEUDAMIENTO','CATEGORIA_SALUD']].copy()
exportar2.index = range(1,11)
exportar2.index.name = 'Posicion'
exportar2.columns = ['Empresa','Ciudad','Total Patrimonio','Total Pasivos','Total Activos','Ratio Endeudamiento','Categoria Salud']
exportar2.to_csv('09_P2_salud_financiera_top10.csv', encoding='utf-8-sig')
print("\n=== PREGUNTA 2: Salud Financiera (Endeudamiento) ===")
print(exportar2.to_string())

# -------------------------------------------------------
# DATASET 3: Top 5 departamentos por ingresos en Comercio
# -------------------------------------------------------
por_depto = comercio_latest.groupby('DEPARTAMENTO').agg(
    Num_Empresas=('NIT','count'),
    Ingreso_Total=('INGRESOS_OP_NUM','sum')
).sort_values('Ingreso_Total', ascending=False).head(5)
total_ingreso = comercio_latest['INGRESOS_OP_NUM'].sum()
por_depto['Porcentaje_Nacional'] = ((por_depto['Ingreso_Total'] / total_ingreso)*100).round(2)
por_depto['Ingreso_Total_Fmt'] = por_depto['Ingreso_Total'].apply(lambda x: f'${x:.2f}B')
por_depto.index.name = 'Departamento'
por_depto.reset_index(inplace=True)
por_depto.index = range(1,6)
por_depto.index.name = 'Posicion'
por_depto[['Departamento','Num_Empresas','Ingreso_Total_Fmt','Porcentaje_Nacional']].to_csv('09_P3_top5_departamentos_comercio.csv', encoding='utf-8-sig')
print("\n=== PREGUNTA 3: Top 5 Departamentos por Ingresos ===")
print(por_depto[['Departamento','Num_Empresas','Ingreso_Total_Fmt','Porcentaje_Nacional']].to_string())

# -------------------------------------------------------
# DATASET 4: Prospectos para Vektraq (ingresos altos + pérdida + endeudamiento bajo)
# -------------------------------------------------------
comercio_latest['ENDEUDAMIENTO'] = (comercio_latest['TOTAL_PASIVOS_NUM'] / comercio_latest['TOTAL_ACTIVOS_NUM']).round(2)
prospectos = comercio_latest[
    (comercio_latest['INGRESOS_OP_NUM'] >= 5.0) &
    (comercio_latest['GANANCIA_NUM'] < 0) &
    (comercio_latest['ENDEUDAMIENTO'] < 0.50)
].sort_values('INGRESOS_OP_NUM', ascending=False).head(10).reset_index(drop=True)
prospectos.index = range(1, len(prospectos)+1)
prospectos.index.name = 'Posicion'
exportar4 = prospectos[['RAZON_SOCIAL','CIUDAD','DEPARTAMENTO','INGRESOS_OP','GANANCIA','ENDEUDAMIENTO','ANO_CORTE']].copy()
exportar4.columns = ['Empresa','Ciudad','Departamento','Ingresos Operacionales','Ganancia_Perdida','Ratio Endeudamiento','Año de Corte']
exportar4.to_csv('09_P4_prospectos_vektraq.csv', encoding='utf-8-sig')
print("\n=== PREGUNTA 4: Prospectos Vektraq (venden mucho, pierden, solventes) ===")
print(exportar4.to_string())

print("\n\n✅ Los 4 datasets han sido generados correctamente.")
