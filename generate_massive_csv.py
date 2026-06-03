import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

data_dir = r"c:\Users\vongo\OneDrive\Escritorio\Proyectos\Agente-BI\datasets_vektra"
os.makedirs(data_dir, exist_ok=True)

print("Generando dataset masivo inspirado en extracciones reales (15,000 filas)...")

n = 15000
platforms = ['Instagram', 'TikTok', 'YouTube', 'LinkedIn', 'Twitter']
post_types = {
    'Instagram': ['Image', 'Carousel', 'Reel'],
    'TikTok': ['Video'],
    'YouTube': ['Video', 'Short'],
    'LinkedIn': ['Text', 'Article', 'Document'],
    'Twitter': ['Text', 'Image', 'Video']
}

data = []
start_date = datetime(2025, 1, 1)

for i in range(n):
    plat = random.choice(platforms)
    ptype = random.choice(post_types[plat])
    
    # Simular una distribución de cuentas y posts realistas (Long tail)
    is_viral = random.random() < 0.05
    base_reach = np.random.lognormal(mean=12, sigma=1.5) if is_viral else np.random.lognormal(mean=8, sigma=1)
    
    reach = int(base_reach)
    impressions = int(reach * random.uniform(1.1, 3.0))
    
    likes = int(reach * random.uniform(0.01, 0.15))
    comments = int(likes * random.uniform(0.01, 0.2))
    shares = int(likes * random.uniform(0.05, 0.4))
    
    # Engagement profundo (Saves)
    if ptype in ['Carousel', 'Article', 'Document']:
        saves = int(reach * random.uniform(0.01, 0.05))
    else:
        saves = int(reach * random.uniform(0.001, 0.01))
        
    date_posted = start_date + timedelta(days=random.randint(0, 500), hours=random.randint(0,23), minutes=random.randint(0,59))
    
    post_url = f"https://www.{plat.lower()}.com/post/{random.randint(100000, 999999999)}"
    profile_id = f"user_{random.randint(1, 500)}"
    
    data.append({
        'post_id': f"P_{i}",
        'profile_id': profile_id,
        'platform': plat,
        'post_type': ptype,
        'date_posted': date_posted.strftime("%Y-%m-%d %H:%M:%S"),
        'post_url': post_url,
        'reach': reach,
        'impressions': impressions,
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'saves': saves,
        'engagement_rate': round((likes + comments + shares + saves) / reach if reach > 0 else 0, 4),
        'is_sponsored': random.choice([True, False]) if random.random() < 0.1 else False
    })

df = pd.DataFrame(data)

# Añadir algo de ruido y valores faltantes naturales
mask = np.random.random(df.shape[0]) < 0.02
df.loc[mask, 'shares'] = np.nan 

output_path = os.path.join(data_dir, "bright_data_massive_sample.csv")
df.to_csv(output_path, index=False)
print(f"Dataset creado exitosamente: {output_path}")
