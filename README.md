# 🛡️ Digital Asset Protection System

> **Upload → Watermark → Store → Detect → Compare → Classify → Display**

An end-to-end MVP for protecting digital image assets using invisible steganographic watermarking, AI-powered feature extraction (MobileNetV2), and perceptual hash similarity detection — deployed on Google Cloud Run.

---

## Architecture Overview

```
┌─────────────┐     HTTP/multipart      ┌──────────────────────────────────┐
│  Streamlit  │ ─────────────────────→  │        FastAPI Backend           │
│  Frontend   │ ←─────────────────────  │                                  │
│  :8501      │       JSON response     │  /upload-original                │
└─────────────┘                         │  /check-image                    │
                                        │  /assets                         │
                                        └───────────┬──────────────────────┘
                                                    │
                        ┌───────────────────────────┼────────────────────┐
                        ▼                           ▼                    ▼
               ┌─────────────────┐      ┌─────────────────┐    ┌────────────────┐
               │  Stegano (LSB)  │      │  MobileNetV2    │    │   SQLite DB    │
               │  Watermarking   │      │  Embeddings     │    │  assets.db     │
               └─────────────────┘      └─────────────────┘    └────────────────┘
```

## Decision Logic

```
Watermark Valid  ─────────────────────────────► Authentic Content ✅
Watermark Missing + High Similarity (>75%)  ──► Unauthorized Copy ⚠️
Watermark Corrupted  ────────────────────────► Tampered Content ⚠️
Low Similarity (<40%)  ──────────────────────► Different Content ❌
```

---

## File Structure

```
digital-asset-protection/
├── backend.py          # FastAPI app (all core logic)
├── frontend.py         # Streamlit UI
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
├── start.sh            # Process launcher script
└── README.md           # This file
```

---

## Local Setup & Run

### Prerequisites
- Python 3.10 or 3.11
- pip

### 1. Install dependencies

```bash
# Clone / download the project folder, then:
cd digital-asset-protection

# (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install CPU-only PyTorch first (smaller, faster install)
pip install torch==2.3.0+cpu torchvision==0.18.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt
```

### 2. Start the backend (Terminal 1)

```bash
python backend.py
# → FastAPI running at http://localhost:8000
# → Auto-downloads MobileNetV2 weights on first run (~14 MB)
```

### 3. Start the frontend (Terminal 2)

```bash
streamlit run frontend.py
# → Opens http://localhost:8501 in your browser
```

### 4. Test via API directly (optional)

```bash
# Register an original image
curl -X POST http://localhost:8000/upload-original \
  -F "file=@your_image.jpg"

# Check a suspected image
curl -X POST http://localhost:8000/check-image \
  -F "file=@suspected_image.jpg"

# List all registered assets
curl http://localhost:8000/assets
```

---

## Example Output

```json
{
  "status": "success",
  "watermark_detected": false,
  "watermark_status": "missing",
  "matched_content_id": "3f8a2b1c-...",
  "matched_filename": "logo.png",
  "hash_similarity": 85.9,
  "ai_similarity": 92.3,
  "decision": "Unauthorized Copy ⚠️",
  "confidence": 89.8,
  "explanation": "ImageHash Similarity: 85.9% | AI Similarity: 92.3% | Final Decision: Unauthorized Copy ⚠️ | Confidence: 89.8%"
}
```

---

## Deploy to Google Cloud Run

### Prerequisites
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- Docker installed
- A GCP project with billing enabled

### Step 1 — Authenticate & set project

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2 — Enable required APIs

```bash
gcloud services enable run.googleapis.com containerregistry.googleapis.com
```

### Step 3 — Build & push Docker image

```bash
# Build
docker build -t gcr.io/YOUR_PROJECT_ID/dap-system .

# Push
docker push gcr.io/YOUR_PROJECT_ID/dap-system
```

### Step 4 — Deploy to Cloud Run

```bash
gcloud run deploy dap-system \
  --image gcr.io/YOUR_PROJECT_ID/dap-system \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8501 \
  --set-env-vars="STREAMLIT_SERVER_HEADLESS=true"
```

### Step 5 — Update API_BASE in frontend.py

After deployment, grab the Cloud Run service URL and update `frontend.py`:

```python
# frontend.py line ~20
API_BASE = "https://dap-system-xxxx-uc.a.run.app"  # ← your Cloud Run URL
```

Then rebuild and redeploy.

### Alternative: Deploy to Railway / Render

Both platforms support Docker deployments via GitHub. Push this folder to a repo, connect to Railway or Render, set `PORT=8501`, and it deploys automatically.

---

## Scalability Roadmap

This MVP uses SQLite and local disk. Here's how to scale to an internet-scale production system:

### 1. Cloud Object Storage
- Replace local file I/O with **Google Cloud Storage (GCS)** or **AWS S3**
- Store watermarked images as objects; use signed URLs for secure, time-limited access
- Add a CDN (Cloud CDN / CloudFront) for global low-latency delivery

### 2. Vector Database for Embeddings
- Replace numpy cosine search with **FAISS** (open-source, in-process, billions of vectors)
- Or **Pinecone / Weaviate / Qdrant** for managed ANN search at scale
- Sub-millisecond similarity search over millions of registered assets

### 3. Real-time Ingestion Pipelines
- **Cloud Pub/Sub + Cloud Run Jobs** for async, event-driven watermark embedding
- **Vertex AI Endpoints** for scalable, GPU-backed MobileNet inference
- **Redis** for embedding cache and rate limiting per user/API key

### 4. Auth & Multi-tenancy
- Add Firebase Auth or Auth0 for user accounts
- Namespace embeddings per organisation in the vector DB
- Role-based access for admin vs viewer

### 5. Observability
- **Cloud Monitoring** dashboards for latency / throughput
- **Structured logging** (JSON) shipped to Cloud Logging
- **OpenTelemetry** tracing for end-to-end request visibility

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Uvicorn |
| Frontend UI | Streamlit |
| Watermarking | Stegano (LSB steganography) |
| AI Features | MobileNetV2 (torchvision, pretrained) |
| Hash Similarity | imagehash (pHash) |
| Deep Similarity | numpy cosine similarity |
| Database | SQLite |
| Containerisation | Docker |
| Cloud Target | Google Cloud Run |

---

## License
MIT — free to use for hackathons, demos, and production.