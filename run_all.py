"""
TxnVerify AI - Unified Process Orchestrator
Starts all 3 sub-services in parallel:
1. WhatsApp Gateway Service (Node.js Express / whatsapp-web.js) - Port 3001
2. Webhook & AI Processing Server (FastAPI / Uvicorn) - Port 8000
3. Control Dashboard & Judge Test Panel (Streamlit) - Port 8501
"""

import sys
import time
import subprocess
import signal
from pathlib import Path

BASE_DIR = Path(__file__).parent


def run_services():
    processes = []
    print("=" * 65)
    print("🚀 Starting TxnVerify AI Autonomous Verification System...")
    print("=" * 65)

    try:
        # 1. Start FastAPI Webhook Server
        print("[1/3] Starting Python Webhook Server (FastAPI on :8000)...")
        p_fastapi = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "webhook_server:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(BASE_DIR)
        )
        processes.append(("FastAPI Webhook Server", p_fastapi))

        # 2. Start WhatsApp Gateway (Node.js) if node_modules exists or can run
        node_modules = BASE_DIR / "node_modules"
        if node_modules.exists():
            print("[2/3] Starting WhatsApp Gateway (Node.js on :3001)...")
            p_node = subprocess.Popen(
                ["node", "whatsapp_gateway.js"],
                cwd=str(BASE_DIR),
                shell=True
            )
            processes.append(("WhatsApp Gateway", p_node))
        else:
            print("[2/3] ℹ️ Node dependencies not yet installed (Run `npm install` to enable live WhatsApp Web JS)")

        # 3. Start Streamlit Dashboard
        print("[3/3] Starting Streamlit Control Dashboard & Judge Panel (Port 8501)...")
        p_streamlit = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "false"],
            cwd=str(BASE_DIR)
        )
        processes.append(("Streamlit Dashboard", p_streamlit))

        print("\n" + "=" * 65)
        print("✅ TxnVerify AI is up and running!")
        print("📊 Streamlit Dashboard:  http://localhost:8501")
        print("🔗 Webhook API Server:   http://localhost:8000")
        print("📱 WhatsApp Gateway:     http://localhost:3001")
        print("=" * 65)
        print("Press Ctrl+C to terminate all services gracefully.\n")

        # Keep running and monitor
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ Process {name} exited unexpectedly with code {proc.returncode}")

    except KeyboardInterrupt:
        print("\n🛑 Shutting down all TxnVerify AI services...")
    finally:
        for name, proc in processes:
            print(f"Terminating {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        print("All processes stopped.")


if __name__ == "__main__":
    run_services()
