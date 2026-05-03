import plotly.graph_objects as go
import plotly.io as pio
import json
import os

print("--- DIAGNÓSTICO DE EXPORTACIÓN ---")
try:
    fig = go.Figure(data=[go.Bar(y=[2, 1, 3])])
    print("[1/2] Objeto de gráfico creado correctamente.")
    
    img_bytes = pio.to_image(fig, format="png", engine="kaleido")
    print(f"[2/2] ¡ÉXITO! Imagen generada: {len(img_bytes)} bytes.")
    
except Exception as e:
    print(f"[X] FALLO CRÍTICO: {str(e)}")
    import traceback
    print(traceback.format_exc())
