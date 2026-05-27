import pandas as pd
import os

def normalize_netflix_genres(input_path="data_sources/Netflix_Titles_Vektra.csv", output_path="data_sources/Netflix_Titles_Clean.csv"):
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra el archivo {input_path}")
        return

    print(f"Iniciando limpieza y normalizacion de generos de Netflix...")
    
    # Cargar datos saltando los metadatos iniciales
    df = pd.read_csv(input_path, skiprows=4)
    
    # El problema: 'listed_in' tiene multiples generos separados por coma
    # Vamos a crear una version donde cada fila es un solo genero para que Vektra pueda contar
    
    # 1. Separar los generos
    df_exploded = df.assign(listed_in=df['listed_in'].str.split(', ')).explode('listed_in')
    
    # 2. Limpieza basica (quitar espacios extra si los hay)
    df_exploded['listed_in'] = df_exploded['listed_in'].str.strip()
    
    # 3. Guardar la version normalizada
    df_exploded.to_csv(output_path, index=False)
    
    print(f"Limpieza completada!")
    print(f"El archivo original tenia {len(df)} filas.")
    print(f"El archivo normalizado tiene {len(df_exploded)} registros.")
    print(f"Ahora puedes usar 'Netflix_Titles_Clean.csv' en Vektra.")

if __name__ == "__main__":
    normalize_netflix_genres()
