"""
TxnVerify AI - Master Process Orchestrator
Start all 3 services together with:
    python run_all.py

To run Streamlit alone:
    streamlit run app.py
"""

import sys
import os
import time
import subprocess
import socket
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def kill_process_on_port(port: int):
    try:
        if sys.platform == "win32":
            cmd = f'powershell -Command "$p = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) {{ Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
    except Exception:
        pass

def main():
    # Detect if user accidentally executed with `streamlit run run_all.py`
    if any("streamlit" in arg.lower() for arg in sys.argv):
        print("\n" + "=" * 65)
        print("⚠️  Notice: You executed `streamlit run run_all.py`.")
        print("    To launch the full stack, use: python run_all.py")
        print("    To launch the UI directly, use: streamlit run app.py")
        print("=" * 65 + "\n")
        return

    print("\n" + "=" * 65)
    print("🚀 TxnVerify AI - Starting Autonomous Verification System")
    print("=" * 65)

    # Clean any stale processes on required ports
    for p in [8501, 8000, 3001]:
        if is_port_in_use(p):
            print(f"[*] Port {p} is busy. Freeing port...")
            kill_process_on_port(p)
            time.sleep(1)

    processes = []

    try:
        # 1. Start Python Webhook Server (FastAPI on :8000)
        print("[1/3] Starting Python Webhook Server (FastAPI on :8000)...")
        p_fastapi = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "webhook_server:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
            cwd=str(BASE_DIR)
        )
        processes.append(("FastAPI Webhook Server", p_fastapi))
        time.sleep(1.5)

        # 2. Start WhatsApp Gateway (Node.js on :3001)
        node_modules = BASE_DIR / "node_modules"
        if node_modules.exists():
            print("[2/3] Starting WhatsApp Gateway (Node.js on :3001)...")
            p_node = subprocess.Popen(
                ["node", "whatsapp_gateway.js"],
                cwd=str(BASE_DIR),
                shell=True
            )
            processes.append(("WhatsApp Gateway", p_node))
            time.sleep(1.5)
        else:
            print("[2/3] ℹ️ node_modules not detected. Run `npm install` for live WhatsApp Web JS.")

        # 3. Start Streamlit Dashboard (:8501)
        print("[3/3] Starting Streamlit Dashboard (Port 8501)...")
        p_streamlit = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
            cwd=str(BASE_DIR)
        )
        processes.append(("Streamlit Dashboard", p_streamlit))

        print("\n" + "=" * 65)
        print("✅ TxnVerify AI is active!")
        print("📊 Dashboard UI:        http://localhost:8501")
        print("🔗 Webhook API Server:  http://localhost:8000")
        print("📱 WhatsApp Gateway:    http://localhost:3001")
        print("=" * 65)
        print("Press Ctrl+C to terminate all services safely.\n")

        # Monitor loop with graceful failure reporting
        dead_reported = set()
        while True:
            time.sleep(3)
            for name, proc in processes:
                if proc.poll() is not None and name not in dead_reported:
                    print(f"⚠️ {name} stopped (exit code {proc.returncode})")
                    dead_reported.add(name)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down all TxnVerify AI services...")
    finally:
        for name, proc in processes:
            print(f"[*] Stopping {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        print("[*] All services stopped cleanly.\n")

if __name__ == "__main__":
    main()
