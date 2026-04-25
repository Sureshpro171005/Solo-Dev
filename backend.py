"""
╔══════════════════════════════════════════════════════════════════╗
║         DIGITAL ASSET PROTECTION SYSTEM - BACKEND               ║
║         FastAPI + MobileNet + Stegano + SQLite                   ║
╚══════════════════════════════════════════════════════════════════╝

SCALABILITY NOTE (For Production Expansion):
─────────────────────────────────────────────
  MVP uses SQLite + local disk. To scale to internet-scale:
  1. Cloud Storage: Replace local file I/O with GCS/S3 buckets
     for media. Use signed URLs for secure access.
  2. Vector Databases: Replace numpy cosine search with FAISS or
     Pinecone for sub-millisecond ANN search over billions of embeddings.
  3. Real-time Pipelines: Add Pub/Sub or Kafka for async ingestion.
     Use Cloud Run Jobs or Vertex AI for heavy model inference.
  4. Distributed Cache: Redis for embedding cache + rate limiting.
  5. Auth Layer: Add Firebase Auth or OAuth2 for multi-tenant access.
  6. Observability: Cloud Monitoring + structured logging + tracing.
"""

import io
import uuid
import json
import sqlite3
import logging
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
import imagehash
import cv2

import torch
import torchvision.models as models
import torchvision.transforms as transforms

from stegano import lsb

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "assets.db"
WATERMARK_MARKER = "DAP_PROTECTED"  # Prefix for watermark strings

# ─────────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────────
def init_db():
    """Initialize SQLite database with required schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id  TEXT UNIQUE NOT NULL,
            filename    TEXT,
            embedding   TEXT NOT NULL,       -- JSON-serialized numpy array
            image_hash  TEXT NOT NULL,       -- perceptual hash string
            watermark   TEXT NOT NULL,       -- watermark payload
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized.")


def save_asset(content_id: str, filename: str, embedding: list,
               image_hash: str, watermark: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO assets
        (content_id, filename, embedding, image_hash, watermark, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (content_id, filename, json.dumps(embedding), image_hash,
          watermark, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_all_assets() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content_id, filename, embedding, image_hash, watermark, created_at FROM assets")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_asset_by_watermark(watermark: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE watermark = ?", (watermark,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "content_id": row[1], "filename": row[2],
            "embedding": json.loads(row[3]), "image_hash": row[4],
            "watermark": row[5], "created_at": row[6]
        }
    return None


# ─────────────────────────────────────────────────────────────────
# AI MODEL — MobileNetV2 FEATURE EXTRACTOR
# ─────────────────────────────────────────────────────────────────
class FeatureExtractor:
    """
    Wraps pretrained MobileNetV2 (ImageNet weights) as a pure
    feature extractor by removing the final classification head.
    Output: 1280-dimensional L2-normalised embedding vector.
    """
    def __init__(self):
        logger.info("Loading MobileNetV2 feature extractor…")
        base = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        # Strip classifier — keep feature layers only
        self.model = torch.nn.Sequential(*list(base.children())[:-1])
        self.model.eval()
        logger.info("Model ready.")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    @torch.no_grad()
    def extract(self, pil_image: Image.Image) -> list:
        """Returns a normalised 1280-d embedding as a Python list."""
        img = pil_image.convert("RGB")
        tensor = self.transform(img).unsqueeze(0)           # (1,3,224,224)
        features = self.model(tensor)                        # (1,1280,1,1)
        vec = features.squeeze().flatten().numpy()           # force flat (1280,)
        vec = vec / (np.linalg.norm(vec) + 1e-8)            # L2 normalise
        return vec.tolist()


# ─────────────────────────────────────────────────────────────────
# WATERMARKING (LSB Steganography via Stegano)
# ─────────────────────────────────────────────────────────────────
def embed_watermark(pil_image: Image.Image, content_id: str) -> tuple[Image.Image, str]:
    """
    Embed an invisible LSB watermark containing the content_id.
    Returns (watermarked_image, watermark_payload).
    """
    import tempfile, os
    payload = f"{WATERMARK_MARKER}:{content_id}"
    img_rgb = pil_image.convert("RGB")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = tmp.name
    tmp.close()
    img_rgb.save(tmp_path, format="PNG")
    watermarked = lsb.hide(tmp_path, payload)
    os.unlink(tmp_path)
    return watermarked, payload


def extract_watermark(pil_image: Image.Image) -> str | None:
    """
    Try to extract LSB watermark from image.
    Returns payload string, or None if extraction fails / no marker found.
    """
    import tempfile, os
    try:
        img_rgb = pil_image.convert("RGB")
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        img_rgb.save(tmp_path, format="PNG")
        secret = lsb.reveal(tmp_path)
        os.unlink(tmp_path)
        if secret and WATERMARK_MARKER in secret:
            return secret
        return None
    except Exception as e:
        logger.warning(f"Watermark extraction failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# SIMILARITY ENGINE
# ─────────────────────────────────────────────────────────────────
def compute_image_hash(pil_image: Image.Image) -> str:
    """Perceptual hash (pHash) — robust to minor resizes/compression."""
    return str(imagehash.phash(pil_image))


def hash_similarity(hash1: str, hash2: str) -> float:
    """
    Return % similarity between two pHash strings.
    Max Hamming distance for 64-bit pHash is 64.
    """
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    distance = h1 - h2                          # Hamming distance
    return round((1 - distance / 64) * 100, 2)


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Cosine similarity → percentage."""
    a = np.array(vec1).flatten()
    b = np.array(vec2).flatten()
    score = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
    return round(score * 100, 2)


# ─────────────────────────────────────────────────────────────────
# DECISION LOGIC
# ─────────────────────────────────────────────────────────────────
def make_decision(watermark_result: str | None, hash_sim: float,
                  ai_sim: float) -> dict:
    """
    Fuse watermark detection + similarity scores into a final verdict.

    Decision matrix:
      ┌─────────────────────────┬──────────────────────────────┐
      │ Watermark found & valid │ "Authentic Content ✅"        │
      │ Watermark missing,      │                              │
      │   high similarity       │ "Unauthorized Copy ⚠️"       │
      │ Watermark corrupted     │ "Tampered Content ⚠️"        │
      │ No match at all         │ "Different Content ❌"        │
      └─────────────────────────┴──────────────────────────────┘
    """
    HIGH_SIM  = 75.0   # above this → Unauthorized Copy
    TAMP_SIM  = 60.0   # between this and HIGH_SIM → Tampered Content

    # Confidence = weighted avg of both similarity scores
    raw_conf = (hash_sim * 0.4 + ai_sim * 0.6)

    if watermark_result == "valid":
        decision = "Authentic Content ✅"
        confidence = min(100, round(raw_conf * 1.05, 1))  # slight boost
    elif watermark_result == "missing":
        if ai_sim >= HIGH_SIM or hash_sim >= HIGH_SIM:
            decision = "Unauthorized Copy ⚠️"
            confidence = round(raw_conf, 1)
        elif ai_sim >= TAMP_SIM or hash_sim >= TAMP_SIM:
            decision = "Tampered Content ⚠️"
            confidence = round(raw_conf * 0.85, 1)
        else:
            decision = "Different Content ❌"
            confidence = round((100 - raw_conf), 1)
    else:
        decision = "Different Content ❌"
        confidence = round((100 - raw_conf), 1)

    confidence = max(0, min(100, confidence))
    return {
        "decision": decision,
        "confidence": confidence,
        "hash_similarity": hash_sim,
        "ai_similarity": ai_sim,
    }


# ─────────────────────────────────────────────────────────────────
# FastAPI APP
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Digital Asset Protection API",
    description="Watermark, store, detect, and classify digital image assets.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise model + DB at startup
extractor = FeatureExtractor()
init_db()

# In-memory cache: content_id → watermarked PNG bytes
watermark_cache: dict[str, bytes] = {}


# ── HEALTH ────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── POST /upload-original ─────────────────────────────────────────
@app.post("/upload-original")
async def upload_original(file: UploadFile = File(...)):
    """
    1. Accept image upload
    2. Embed invisible LSB watermark
    3. Extract MobileNet embedding
    4. Compute pHash
    5. Store everything in SQLite
    6. Return content_id + metadata
    """
    raw = await file.read()
    try:
        pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    content_id = str(uuid.uuid4())

    # Watermark
    watermarked_img, watermark_payload = embed_watermark(pil_img, content_id)

    # Embedding
    embedding = extractor.extract(pil_img)

    # pHash
    img_hash = compute_image_hash(pil_img)

    # Persist
    save_asset(content_id, file.filename or "unknown",
               embedding, img_hash, watermark_payload)

    # Cache watermarked image in memory for download
    wm_buf = io.BytesIO()
    watermarked_img.save(wm_buf, format="PNG")
    watermark_cache[content_id] = wm_buf.getvalue()

    logger.info(f"Registered asset {content_id} ({file.filename})")

    return JSONResponse({
        "status": "success",
        "content_id": content_id,
        "filename": file.filename,
        "watermark": watermark_payload,
        "image_hash": img_hash,
        "message": "Original image registered and watermarked.",
    })


# ── GET /download-watermarked/{content_id} ────────────────────────
@app.get("/download-watermarked/{content_id}")
def download_watermarked(content_id: str):
    """Return the watermarked PNG so the user can test authentic detection."""
    from fastapi.responses import Response
    if content_id not in watermark_cache:
        raise HTTPException(status_code=404,
                            detail="Watermarked image not in memory. Please re-register.")
    return Response(
        content=watermark_cache[content_id],
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=watermarked_{content_id[:8]}.png"},
    )


# ── POST /check-image ─────────────────────────────────────────────
@app.post("/check-image")
async def check_image(file: UploadFile = File(...)):
    """
    1. Accept suspected image
    2. Try watermark extraction
    3. Compare against all stored assets via hash + AI similarity
    4. Return verdict with confidence score
    """
    raw = await file.read()
    try:
        pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    assets = get_all_assets()
    if not assets:
        raise HTTPException(status_code=404,
                            detail="No registered assets in database.")

    # ── Step 1: Watermark extraction ──────────────────────────────
    try:
        watermark_payload = extract_watermark(pil_img)
    except Exception as e:
        logger.warning(f"Watermark extraction crashed: {e}")
        watermark_payload = None

    watermark_status = "missing"
    matched_content_id = None
    matched_filename = None

    if watermark_payload:
        if WATERMARK_MARKER in watermark_payload:
            stored = get_asset_by_watermark(watermark_payload)
            if stored:
                watermark_status = "valid"
                matched_content_id = stored["content_id"]
                matched_filename = stored["filename"]
            else:
                watermark_status = "corrupted"
        else:
            watermark_status = "corrupted"

    # ── Step 2: Similarity against best match ─────────────────────
    try:
        query_embedding = extractor.extract(pil_img)
        query_hash = compute_image_hash(pil_img)
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Feature extraction failed: {str(e)}")

    best_hash_sim = 0.0
    best_ai_sim = 0.0
    best_asset_id = None
    best_asset_file = None

    logger.info(f"Query hash: {query_hash}")
    logger.info(f"Query embedding length: {len(query_embedding)}")
    logger.info(f"Number of assets to compare: {len(assets)}")

    for row in assets:
        try:
            cid, fname, emb_json, stored_hash, _, _ = row
            stored_emb = json.loads(emb_json)
            logger.info(f"Comparing with asset: {fname} | stored_hash: {stored_hash} | emb_len: {len(stored_emb)}")
            h_sim = hash_similarity(query_hash, stored_hash)
            a_sim = cosine_similarity(query_embedding, stored_emb)
            logger.info(f"  hash_sim={h_sim}  ai_sim={a_sim}")
            combined = h_sim * 0.4 + a_sim * 0.6
            best_combined = best_hash_sim * 0.4 + best_ai_sim * 0.6
            if combined > best_combined:
                best_hash_sim = h_sim
                best_ai_sim = a_sim
                best_asset_id = cid
                best_asset_file = fname
        except Exception as e:
            logger.warning(f"Skipping asset due to error: {e}")
            continue

    # ── Step 3: Decision ──────────────────────────────────────────
    result = make_decision(watermark_status, best_hash_sim, best_ai_sim)

    response = {
        "status": "success",
        "watermark_detected": watermark_payload is not None,
        "watermark_status": watermark_status,
        "matched_content_id": matched_content_id or best_asset_id,
        "matched_filename": matched_filename or best_asset_file,
        "hash_similarity": result["hash_similarity"],
        "ai_similarity": result["ai_similarity"],
        "decision": result["decision"],
        "confidence": result["confidence"],
        "explanation": (
            f"ImageHash Similarity: {result['hash_similarity']}% | "
            f"AI Similarity: {result['ai_similarity']}% | "
            f"Final Decision: {result['decision']} | "
            f"Confidence: {result['confidence']}%"
        ),
    }

    logger.info(f"Check result: {result['decision']} (conf={result['confidence']}%)")
    return JSONResponse(response)


# ── GET /assets ───────────────────────────────────────────────────
@app.get("/assets")
def list_assets():
    """List all registered assets (without embeddings for brevity)."""
    rows = get_all_assets()
    return {"count": len(rows), "assets": [
        {"content_id": r[0], "filename": r[1],
         "image_hash": r[3], "created_at": r[5]}
        for r in rows
    ]}


# ── ENTRYPOINT ────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=False)