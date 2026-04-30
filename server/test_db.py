from src.database import engine, text
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print(f"Connection SUCCESS: {res.fetchone()}")
except Exception as e:
    print(f"Connection FAILED: {e}")
