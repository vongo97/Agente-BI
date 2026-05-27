import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_strategic_dataset(output_path="data_sources/ecommerce_50k_strategic.csv", rows=50000):
    print(f"🚀 Iniciando generación de {rows} registros estratégicos...")
    
    # Configuración de categorías y productos
    categories = {
        'Electrónica': ['Smartphone X1', 'Laptop Pro', 'Smartwatch v2', 'Auriculares ANC', 'Tablet Air'],
        'Hogar': ['Cafetera Express', 'Robot Aspirador', 'Lámpara Inteligente', 'Silla Ergonómica'],
        'Moda': ['Camiseta Premium', 'Jeans Slim Fit', 'Zapatillas Urban', 'Chaqueta Invierno'],
        'Deportes': ['Mancuernas Set', 'Yoga Mat', 'Bicicleta Montaña', 'Proteína Whey']
    }
    
    cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga']
    channels = ['Organic Search', 'Paid Ads', 'Social Media', 'Direct', 'Email']
    
    data = []
    start_date = datetime(2022, 1, 1)
    
    cat_list = list(categories.keys())
    
    for i in range(rows):
        # Fecha aleatoria en los últimos 3 años
        days_offset = np.random.randint(0, 1095)
        date = start_date + timedelta(days=days_offset)
        
        # Selección de categoría y producto
        category = np.random.choice(cat_list)
        product = np.random.choice(categories[category])
        
        # Precio base según categoría
        if category == 'Electrónica': base_price = np.random.uniform(200, 1200)
        elif category == 'Hogar': base_price = np.random.uniform(50, 400)
        elif category == 'Moda': base_price = np.random.uniform(20, 150)
        else: base_price = np.random.uniform(10, 200)
        
        quantity = np.random.randint(1, 5)
        discount = 0
        
        # --- INSERCIÓN DE PATRONES ESTRATÉGICOS (EL "GANCHO" PARA VEKTRA) ---
        
        # 1. Anomalía: Descuentos agresivos en Valencia los fines de semana
        city = np.random.choice(cities)
        if city == 'Valencia' and date.weekday() >= 5:
            discount = np.random.uniform(0.2, 0.4) # 20-40% descuento
            
        # 2. Estacionalidad: Aumento de ventas en Electrónica en Noviembre (Black Friday)
        if date.month == 11 and category == 'Electrónica':
            quantity += np.random.randint(2, 6)
            
        # 3. Bajo Margen: La categoría 'Moda' tiene devoluciones altas (simulado con profit negativo)
        profit_margin = np.random.uniform(0.1, 0.4)
        if category == 'Moda' and np.random.random() > 0.8:
            profit_margin = -0.1 # Pérdida por logística
            
        total_sales = (base_price * quantity) * (1 - discount)
        profit = total_sales * profit_margin
        
        data.append({
            'Order_ID': f'ORD-{100000 + i}',
            'Date': date.strftime('%Y-%m-%d'),
            'Customer_ID': f'CUST-{np.random.randint(1000, 5000)}',
            'Product': product,
            'Category': category,
            'City': city,
            'Channel': np.random.choice(channels),
            'Price_Unit': round(base_price, 2),
            'Quantity': quantity,
            'Discount': round(discount, 2),
            'Total_Sales': round(total_sales, 2),
            'Profit': round(profit, 2),
            'Status': np.random.choice(['Completed', 'Completed', 'Completed', 'Cancelled'], p=[0.9, 0.05, 0.03, 0.02])
        })
        
        if i % 10000 == 0 and i > 0:
            print(f"✅ Generadas {i} filas...")

    df = pd.DataFrame(data)
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"\n✨ ¡Dataset completado! Guardado en: {output_path}")
    print(f"📊 Resumen: {len(df)} filas, {len(df.columns)} columnas.")
    print(f"💡 Tip: Sube este archivo a Vektra y pregunta por las pérdidas en Valencia o la rentabilidad de Moda.")

if __name__ == "__main__":
    generate_strategic_dataset()
