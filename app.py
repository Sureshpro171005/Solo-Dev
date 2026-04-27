import subprocess
import threading
import time
import sys
import os

# ── Start FastAPI backend in background ──
def start_backend():
    subprocess.Popen(
        [sys.executable, "backend.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# Launch backend thread
thread = threading.Thread(target=start_backend, daemon=True)
thread.start()

# Wait for backend to fully start
time.sleep(4)

# ── Now run the frontend ──
os.system(f"{sys.executable} -m streamlit run frontend.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true")