# ─────────────────────────────────────────────────────────────────
# Dockerfile — Digital Asset Protection System
# Runs BOTH FastAPI (port 8000) and Streamlit (port 8501) via a
# simple shell script. For Cloud Run, expose 8501 and set
#   --allow-unauthenticated
# ─────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# System deps for OpenCV headless + torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install CPU-only torch first (smaller image for cloud)
RUN pip install --no-cache-dir \
    torch==2.3.0+cpu torchvision==0.18.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py frontend.py start.sh ./

RUN chmod +x start.sh

# Pre-download MobileNetV2 weights so first request is instant
RUN python -c "import torchvision.models as m; m.mobilenet_v2(weights=m.MobileNet_V2_Weights.DEFAULT)"

EXPOSE 8000 8501

CMD ["./start.sh"]