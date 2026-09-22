import pandas as pd
import os

filepath = r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\datasets_vektra\1_multi_platform_engagement.csv"
df = pd.read_csv(filepath)

# Pregunta 1: Formato con mayor Engagement Profundo (Saves + Shares) en proporción al Reach
df['Deep_Engagement'] = df['Saves'] + df['Shares']
df['Deep_Eng_Rate'] = df['Deep_Engagement'] / df['Reach']
q1_res = df.groupby('Format')['Deep_Eng_Rate'].mean().sort_values(ascending=False)

# Pregunta 2: Mejor retención algorítmica (Impressions / Reach) por plataforma
df['Imp_Reach_Ratio'] = df['Impressions'] / df['Reach']
q2_res = df.groupby('Platform')['Imp_Reach_Ratio'].mean().sort_values(ascending=False)

print("--- RESULTADOS Q1 (Deep Engagement Rate por Formato) ---")
print(q1_res.head(3))

print("\n--- RESULTADOS Q2 (Impressions / Reach Ratio por Plataforma) ---")
print(q2_res.head(3))
