import sqlite3
import pandas as pd
import os

# Definir la ruta de la base de datos en la carpeta server
db_path = os.path.join("server", "test_bi.db")

def create_test_data():
    conn = sqlite3.connect(db_path)
    
    # Datos de ventas de prueba
    data = {
        'id': range(1, 11),
        'producto': ['Laptop', 'Mouse', 'Monitor', 'Teclado', 'Laptop', 'Mouse', 'Monitor', 'Cascos', 'Teclado', 'Monitor'],
        'unidades': [2, 10, 5, 8, 1, 15, 3, 12, 4, 7],
        'precio_unitario': [1200, 25, 200, 45, 1250, 20, 210, 80, 50, 195],
        'fecha': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', 
                  '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10']
    }
    
    df = pd.DataFrame(data)
    df.to_sql('ventas', conn, if_exists='replace', index=False)
    
    print(f"✅ Base de datos de prueba creada en: {db_path}")
    print(f"🔗 URL para el Agente BI: sqlite:///test_bi.db")
    
    conn.close()

if __name__ == "__main__":
    create_test_data()
