import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

# Crear carpeta de datos si no existe
data_dir = "datasets_vektra"
os.makedirs(data_dir, exist_ok=True)

np.random.seed(42)

def random_dates(start_date, end_date, n=1000):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    delta = end - start
    return [start + timedelta(days=random.randint(0, delta.days)) for _ in range(n)]

# 1. Dataset: Multi-Platform Engagement
def gen_multi_platform():
    n = 2000
    platforms = ['Instagram', 'TikTok', 'LinkedIn', 'YouTube', 'Twitter']
    formats = {'Instagram': ['Reel', 'Carousel', 'Post'], 
               'TikTok': ['Short Video'], 
               'LinkedIn': ['Text', 'Article', 'Video'], 
               'YouTube': ['Long Video', 'Short'], 
               'Twitter': ['Thread', 'Text']}
    
    data = []
    for _ in range(n):
        plat = random.choice(platforms)
        form = random.choice(formats[plat])
        reach = int(np.random.lognormal(mean=9, sigma=1.5))
        impressions = int(reach * random.uniform(1.1, 1.8))
        likes = int(reach * random.uniform(0.01, 0.1))
        comments = int(likes * random.uniform(0.05, 0.2))
        shares = int(likes * random.uniform(0.1, 0.5))
        saves = int(likes * random.uniform(0.05, 0.4)) if plat in ['Instagram', 'TikTok'] else 0
        
        data.append([plat, form, reach, impressions, likes, comments, shares, saves])
        
    df = pd.DataFrame(data, columns=['Platform', 'Format', 'Reach', 'Impressions', 'Likes', 'Comments', 'Shares', 'Saves'])
    df['Engagement_Rate_Reach'] = ((df['Likes'] + df['Comments'] + df['Shares'] + df['Saves']) / df['Reach']).round(4)
    df.to_csv(os.path.join(data_dir, '1_multi_platform_engagement.csv'), index=False)

# 2. Dataset: Social Media Demographics 2025
def gen_demographics():
    n = 2500
    genders = ['Female', 'Male', 'Non-Binary']
    ages = ['18-24', '25-34', '35-44', '45-54']
    countries = ['USA', 'Spain', 'Mexico', 'UK', 'Colombia']
    
    data = {
        'User_ID': [f'U{str(i).zfill(5)}' for i in range(1, n+1)],
        'Gender': np.random.choice(genders, n, p=[0.5, 0.45, 0.05]),
        'Age_Group': np.random.choice(ages, n, p=[0.4, 0.35, 0.15, 0.1]),
        'Country': np.random.choice(countries, n),
        'Followers': np.random.randint(100, 50000, n),
        'Avg_Time_Spent_Mins': np.random.randint(10, 180, n),
        'Conversion_Status': np.random.choice([1, 0], n, p=[0.08, 0.92])
    }
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(data_dir, '2_social_demographics.csv'), index=False)

# 3. Dataset: Sentiment Analysis & Reactions
def gen_sentiment():
    n = 1500
    dates = random_dates('2025-01-01', '2026-05-01', n)
    sentiments = ['Positive', 'Neutral', 'Negative']
    
    data = {
        'Post_Date': dates,
        'Topic': np.random.choice(['Tech', 'Fashion', 'Finance', 'Health', 'Education'], n),
        'Sentiment': np.random.choice(sentiments, n, p=[0.6, 0.25, 0.15]),
        'Love_Reacts': np.random.randint(0, 5000, n),
        'Wow_Reacts': np.random.randint(0, 1000, n),
        'Haha_Reacts': np.random.randint(0, 2000, n),
        'Sad_Reacts': np.random.randint(0, 200, n),
        'Angry_Reacts': np.random.randint(0, 300, n),
    }
    df = pd.DataFrame(data)
    # Ajustar reacciones según sentimiento
    df.loc[df['Sentiment'] == 'Negative', 'Angry_Reacts'] *= 5
    df.loc[df['Sentiment'] == 'Negative', 'Sad_Reacts'] *= 3
    df.loc[df['Sentiment'] == 'Positive', 'Love_Reacts'] *= 3
    
    df = df.sort_values('Post_Date')
    df.to_csv(os.path.join(data_dir, '3_sentiment_reactions.csv'), index=False)

if __name__ == '__main__':
    print("Generando datasets...")
    gen_multi_platform()
    gen_demographics()
    gen_sentiment()
    print(f"Datasets creados en la carpeta: {os.path.abspath(data_dir)}")
