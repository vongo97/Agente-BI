import pandas as pd

def analyze_genres():
    df = pd.read_csv("data_sources/Netflix_Titles_Clean.csv")
    
    # Contar generos
    genre_counts = df['listed_in'].value_counts()
    
    print("--- TOP 10 GÉNEROS SATURADOS ---")
    print(genre_counts.head(10))
    
    print("\n--- GÉNEROS CON BAJA COMPETENCIA (POTENCIAL NICHO) ---")
    # Generos que tienen pocos titulos pero podrian ser interesantes
    print(genre_counts.tail(10))
    
    # Analisis por tipo (Movie vs TV Show)
    print("\n--- DISTRIBUCIÓN POR TIPO ---")
    print(df['type'].value_counts())

if __name__ == "__main__":
    analyze_genres()
