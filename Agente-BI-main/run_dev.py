import subprocess
import os
import sys
import time
import signal

def run_services():
    root_dir = os.getcwd()
    server_dir = os.path.join(root_dir, "server")
    client_dir = os.path.join(root_dir, "client")

    print("🚀 Iniciando Agente BI v2.5 (React + FastAPI)...")

    # 1. Iniciar Backend (FastAPI)
    print("📡 Levantando Backend en http://0.0.0.0:8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=server_dir
    )

    # 2. Iniciar Frontend (Next.js)
    print("💻 Levantando Frontend en http://0.0.0.0:3000...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "-H", "0.0.0.0"],
        cwd=client_dir,
        shell=True
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servicios...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("✅ Servicios terminados.")

if __name__ == "__main__":
    run_services()
