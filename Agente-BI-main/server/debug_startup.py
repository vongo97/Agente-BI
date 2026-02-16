import sys
import os
import traceback

# Asegurar que estamos en el directorio correcto virtualmente
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..')) # Para imports tipo src.

print(f"Testing import of main.py from {current_dir}...")

try:
    import main
    print("✅ SUCCESS: main.py imported correctly.")
except Exception as e:
    print(f"❌ ERROR importing main: {e}")
    traceback.print_exc()
