"""
╔══════════════════════════════════════════════════════════════════╗
║         DIGITAL ASSET PROTECTION SYSTEM - FRONTEND              ║
║         Streamlit UI — Upload · Watermark · Detect · Classify   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import io
import requests
import streamlit as st
from PIL import Image

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"   # Change to Cloud Run URL for deployment

st.set_page_config(
    page_title="Digital Asset Protection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# CUSTOM CSS — Dark cyberpunk aesthetic with amber accents
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;400;600;700;900&display=swap');

/* ── Root palette ── */
:root {
    --bg:        #0a0c10;
    --surface:   #111318;
    --border:    #1e2330;
    --amber:     #f5a623;
    --amber-dim: #b87a1a;
    --cyan:      #00d4ff;
    --green:     #00ff88;
    --red:       #ff4466;
    --text:      #c8d0e0;
    --muted:     #5a6080;
}

/* ── Base ── */
html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Exo 2', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem !important; max-width: 1400px; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0d1117 0%, #111827 50%, #0d1117 100%);
    border: 1px solid var(--border);
    border-top: 3px solid var(--amber);
    border-radius: 4px;
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at 30% 40%, rgba(245,166,35,0.06) 0%, transparent 60%);
    pointer-events: none;
}
.hero h1 {
    font-family: 'Exo 2', sans-serif !important;
    font-weight: 900 !important;
    font-size: 2.4rem !important;
    color: #fff !important;
    letter-spacing: 0.04em;
    margin: 0 0 0.4rem 0 !important;
}
.hero h1 span { color: var(--amber); }
.hero p {
    color: var(--muted) !important;
    font-size: 0.95rem !important;
    font-family: 'Share Tech Mono', monospace !important;
    margin: 0 !important;
}

/* ── Panel cards ── */
.panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.6rem;
    height: 100%;
}
.panel-title {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: var(--amber);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.6rem;
}

/* ── Metric boxes ── */
.metric-row { display: flex; gap: 1rem; margin: 1rem 0; }
.metric-box {
    flex: 1;
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem;
    text-align: center;
}
.metric-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.metric-value {
    font-family: 'Exo 2', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    margin-top: 0.2rem;
}

/* ── Decision badge ── */
.verdict {
    border-radius: 4px;
    padding: 1.2rem 1.6rem;
    margin: 1rem 0;
    font-family: 'Exo 2', sans-serif;
    font-weight: 700;
    font-size: 1.3rem;
    text-align: center;
    border-left: 4px solid;
}
.verdict-auth  { background: rgba(0,255,136,0.08); border-color: var(--green); color: var(--green); }
.verdict-copy  { background: rgba(245,166,35,0.08); border-color: var(--amber); color: var(--amber); }
.verdict-tamper{ background: rgba(245,166,35,0.08); border-color: var(--amber); color: var(--amber); }
.verdict-diff  { background: rgba(255,68,102,0.08); border-color: var(--red);   color: var(--red); }

/* ── Progress bar ── */
.sim-bar-wrap { margin: 0.5rem 0 1rem; }
.sim-bar-label { font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:var(--muted); margin-bottom:0.3rem; display:flex; justify-content:space-between; }
.sim-bar-bg { background:#1a1f2e; border-radius:2px; height:8px; }
.sim-bar-fill { height:8px; border-radius:2px; transition: width 0.6s ease; }
.bar-hash  { background: linear-gradient(90deg, var(--cyan), #0088aa); }
.bar-ai    { background: linear-gradient(90deg, var(--amber), var(--amber-dim)); }
.bar-conf  { background: linear-gradient(90deg, var(--green), #00aa55); }

/* ── Status pill ── */
.pill {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'Share Tech Mono', monospace;
    letter-spacing: 0.08em;
}
.pill-ok   { background: rgba(0,255,136,0.15); color: var(--green); border: 1px solid rgba(0,255,136,0.3); }
.pill-warn { background: rgba(245,166,35,0.15); color: var(--amber); border: 1px solid rgba(245,166,35,0.3); }
.pill-err  { background: rgba(255,68,102,0.15); color: var(--red);   border: 1px solid rgba(255,68,102,0.3); }

/* ── Streamlit file uploader ── */
[data-testid="stFileUploader"] {
    background: #0d1117 !important;
    border: 1px dashed var(--border) !important;
    border-radius: 4px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--amber) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--amber) !important;
    color: #000 !important;
    font-family: 'Exo 2', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 0.55rem 2rem !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Mono tag ── */
.mono { font-family: 'Share Tech Mono', monospace; color: var(--muted); font-size: 0.8rem; }
.highlight { color: var(--amber); }

/* ── Timeline step ── */
.step-row { display:flex; align-items:flex-start; gap:1rem; margin:0.8rem 0; }
.step-num { background:var(--amber); color:#000; font-weight:700; font-size:0.75rem;
            width:22px; height:22px; border-radius:50%; display:flex; align-items:center;
            justify-content:center; flex-shrink:0; margin-top:0.1rem; }
.step-text { font-size:0.9rem; color:var(--text); }
.step-text b { color:#fff; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def api_upload_original(image_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/upload-original",
        files={"file": (filename, image_bytes, "image/png")},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def api_check_image(image_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/check-image",
        files={"file": (filename, image_bytes, "image/png")},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def api_list_assets() -> dict:
    resp = requests.get(f"{API_BASE}/assets", timeout=10)
    resp.raise_for_status()
    return resp.json()


def sim_bar(label: str, value: float, bar_class: str):
    st.markdown(f"""
    <div class="sim-bar-wrap">
        <div class="sim-bar-label">
            <span>{label}</span><span class="highlight">{value:.1f}%</span>
        </div>
        <div class="sim-bar-bg">
            <div class="sim-bar-fill {bar_class}" style="width:{min(value,100):.1f}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def verdict_html(decision: str) -> str:
    if "✅" in decision:
        cls = "verdict-auth"
    elif "Unauthorized" in decision:
        cls = "verdict-copy"
    elif "Tampered" in decision:
        cls = "verdict-tamper"
    else:
        cls = "verdict-diff"
    return f'<div class="verdict {cls}">{decision}</div>'


# ─────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🛡️ Digital <span>Asset Protection</span> System</h1>
    <p>► Invisible watermarking · AI feature extraction · Real-time similarity detection · Tamper classification</p>
</div>
""", unsafe_allow_html=True)

# API health check (silent)
api_online = False
try:
    r = requests.get(f"{API_BASE}/health", timeout=3)
    api_online = r.status_code == 200
except Exception:
    pass

status_pill = '<span class="pill pill-ok">● API ONLINE</span>' if api_online else \
              '<span class="pill pill-err">● API OFFLINE — start backend.py</span>'
st.markdown(status_pill, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# MAIN LAYOUT — two columns
# ─────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════════════════
# LEFT — Register Original
# ══════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">◈ Register Original Asset</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom:1rem;">
    <div class="step-row"><div class="step-num">1</div><div class="step-text"><b>Upload</b> original image to protect</div></div>
    <div class="step-row"><div class="step-num">2</div><div class="step-text"><b>Invisible watermark</b> embedded via LSB steganography</div></div>
    <div class="step-row"><div class="step-num">3</div><div class="step-text"><b>MobileNet embedding</b> + perceptual hash stored in DB</div></div>
    </div>
    """, unsafe_allow_html=True)

    orig_file = st.file_uploader(
        "Drop your original image here",
        type=["jpg", "jpeg", "png", "webp"],
        key="orig_uploader",
        label_visibility="collapsed",
    )

    if orig_file:
        img_bytes = orig_file.read()
        pil = Image.open(io.BytesIO(img_bytes))
        st.image(pil, use_container_width=True, caption=orig_file.name)

        if st.button("🔐  Register & Watermark", key="btn_register"):
            if not api_online:
                st.error("Backend API is offline. Please start backend.py first.")
            else:
                with st.spinner("Embedding watermark + extracting features…"):
                    try:
                        result = api_upload_original(img_bytes, orig_file.name)
                        st.success("Asset registered successfully!")
                        st.markdown(f"""
                        <div style="margin-top:1rem;">
                            <div class="panel-title">Registration Record</div>
                            <div class="mono">CONTENT ID</div>
                            <div style="color:#fff; font-family:'Share Tech Mono',monospace; font-size:0.85rem; word-break:break-all; margin:0.2rem 0 0.8rem;">
                                {result.get('content_id','')}
                            </div>
                            <div class="mono">WATERMARK PAYLOAD</div>
                            <div style="color:var(--amber); font-family:'Share Tech Mono',monospace; font-size:0.8rem; word-break:break-all; margin:0.2rem 0 0.8rem;">
                                {result.get('watermark','')}
                            </div>
                            <div class="mono">PERCEPTUAL HASH</div>
                            <div style="color:var(--cyan); font-family:'Share Tech Mono',monospace; font-size:0.8rem; margin-top:0.2rem;">
                                {result.get('image_hash','')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.session_state["last_registered"] = result

                        # Download watermarked image button
                        content_id = result.get('content_id', '')
                        wm_url = f"{API_BASE}/download-watermarked/{content_id}"
                        try:
                            wm_resp = requests.get(wm_url, timeout=10)
                            if wm_resp.status_code == 200:
                                st.download_button(
                                    label="⬇️ Download Watermarked Image",
                                    data=wm_resp.content,
                                    file_name=f"watermarked_{content_id[:8]}.png",
                                    mime="image/png",
                                    help="Use this watermarked PNG to test Authentic Content detection"
                                )
                                st.info("💡 Upload this watermarked PNG on the right side to get 'Authentic Content ✅'")
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Registered assets table
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">◈ Registered Assets</div>', unsafe_allow_html=True)
    if api_online:
        try:
            assets_data = api_list_assets()
            cnt = assets_data.get("count", 0)
            st.markdown(f'<span class="pill pill-ok">{cnt} asset{"s" if cnt != 1 else ""} in database</span>',
                        unsafe_allow_html=True)
            for a in assets_data.get("assets", [])[:5]:
                st.markdown(f"""
                <div style="border-top:1px solid var(--border); padding:0.6rem 0; margin-top:0.4rem;">
                    <span class="mono">{a['filename']}</span>
                    <div style="font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:var(--muted); margin-top:0.15rem;">
                        {a['content_id'][:24]}… · {a['created_at'][:19]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if cnt > 5:
                st.markdown(f'<div class="mono" style="margin-top:0.5rem;">… and {cnt-5} more</div>',
                            unsafe_allow_html=True)
        except Exception:
            st.markdown('<span class="pill pill-warn">Could not load assets</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill pill-err">API offline</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# RIGHT — Analyse Suspected Image
# ══════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">◈ Analyse Suspected Image</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom:1rem;">
    <div class="step-row"><div class="step-num">1</div><div class="step-text"><b>Upload</b> suspected / found image</div></div>
    <div class="step-row"><div class="step-num">2</div><div class="step-text">System attempts <b>watermark extraction</b></div></div>
    <div class="step-row"><div class="step-num">3</div><div class="step-text"><b>Hash + AI similarity</b> computed against all stored assets</div></div>
    <div class="step-row"><div class="step-num">4</div><div class="step-text">Final <b>classification + confidence score</b> returned</div></div>
    </div>
    """, unsafe_allow_html=True)

    susp_file = st.file_uploader(
        "Drop suspected image here",
        type=["jpg", "jpeg", "png", "webp"],
        key="susp_uploader",
        label_visibility="collapsed",
    )

    if susp_file:
        img_bytes_s = susp_file.read()
        pil_s = Image.open(io.BytesIO(img_bytes_s))
        st.image(pil_s, use_container_width=True, caption=susp_file.name)

        if st.button("🔍  Analyse Image", key="btn_check"):
            if not api_online:
                st.error("Backend API is offline. Please start backend.py first.")
            else:
                with st.spinner("Extracting watermark · Computing similarity…"):
                    try:
                        result = api_check_image(img_bytes_s, susp_file.name)

                        # ── Watermark status ──────────────────────────────
                        wm_status = result.get("watermark_status", "missing")
                        wm_detected = result.get("watermark_detected", False)

                        if wm_status == "valid":
                            wm_pill = '<span class="pill pill-ok">✓ WATERMARK VALID</span>'
                        elif wm_status == "corrupted":
                            wm_pill = '<span class="pill pill-warn">⚠ WATERMARK CORRUPTED</span>'
                        else:
                            wm_pill = '<span class="pill pill-err">✗ NO WATERMARK FOUND</span>'

                        st.markdown(f"""
                        <div style="margin:1rem 0 0.5rem;">
                            <div class="panel-title">Watermark Detection</div>
                            {wm_pill}
                        </div>
                        """, unsafe_allow_html=True)

                        if result.get("matched_content_id"):
                            st.markdown(f"""
                            <div class="mono" style="margin-top:0.5rem;">
                                MATCHED ASSET: <span class="highlight">{result.get('matched_filename','?')}</span><br>
                                ID: {result.get('matched_content_id','')[:32]}…
                            </div>
                            """, unsafe_allow_html=True)

                        # ── Similarity bars ───────────────────────────────
                        st.markdown('<div class="panel-title" style="margin-top:1.2rem;">Similarity Analysis</div>',
                                    unsafe_allow_html=True)
                        hash_sim = result.get("hash_similarity", 0)
                        ai_sim   = result.get("ai_similarity", 0)
                        conf     = result.get("confidence", 0)

                        sim_bar("ImageHash Similarity",   hash_sim, "bar-hash")
                        sim_bar("AI Embedding Similarity", ai_sim,  "bar-ai")
                        sim_bar("Confidence Score",        conf,     "bar-conf")

                        # ── Metric boxes ──────────────────────────────────
                        st.markdown(f"""
                        <div class="metric-row">
                            <div class="metric-box">
                                <div class="metric-label">ImageHash</div>
                                <div class="metric-value" style="color:var(--cyan)">{hash_sim:.0f}%</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-label">AI Similarity</div>
                                <div class="metric-value" style="color:var(--amber)">{ai_sim:.0f}%</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-label">Confidence</div>
                                <div class="metric-value" style="color:var(--green)">{conf:.0f}%</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # ── Verdict ───────────────────────────────────────
                        decision = result.get("decision", "Unknown")
                        st.markdown('<div class="panel-title">Final Verdict</div>', unsafe_allow_html=True)
                        st.markdown(verdict_html(decision), unsafe_allow_html=True)

                        # ── Explanation ───────────────────────────────────
                        st.markdown(f"""
                        <div style="background:#0d1117; border:1px solid var(--border); border-radius:4px;
                                    padding:1rem; margin-top:1rem; font-family:'Share Tech Mono',monospace;
                                    font-size:0.78rem; color:var(--muted); line-height:1.8;">
                            ImageHash Similarity : <span class="highlight">{hash_sim:.1f}%</span><br>
                            AI Similarity        : <span class="highlight">{ai_sim:.1f}%</span><br>
                            Watermark Status     : <span class="highlight">{wm_status.upper()}</span><br>
                            Final Decision       : <span style="color:#fff;">{decision}</span><br>
                            Confidence           : <span class="highlight">{conf:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)

                        # Legend
                        st.markdown("""
                        <div style="margin-top:1.2rem; font-size:0.78rem; color:var(--muted);">
                            <b style="color:#fff;">Decision logic:</b><br>
                            ✅ Watermark valid → Authentic Content<br>
                            ⚠️ No watermark + high similarity → Unauthorized Copy<br>
                            ⚠️ Corrupted watermark → Tampered Content<br>
                            ❌ Low similarity → Different Content
                        </div>
                        """, unsafe_allow_html=True)

                    except requests.HTTPError as e:
                        st.error(f"API error: {e.response.text if e.response else e}")
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# FOOTER — Scalability note
# ─────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--cyan);
            border-radius:4px; padding:1.4rem 1.8rem; margin-top:1rem;">
    <div class="panel-title" style="color:var(--cyan);">◈ Scalability Roadmap — MVP → Production</div>
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:1.2rem; margin-top:0.5rem;">
        <div>
            <div style="color:#fff; font-weight:600; margin-bottom:0.4rem;">☁ Cloud Storage</div>
            <div style="font-size:0.83rem; color:var(--muted);">Replace local disk with GCS/S3.
            Signed URLs for secure media access. CDN layer for global delivery.</div>
        </div>
        <div>
            <div style="color:#fff; font-weight:600; margin-bottom:0.4rem;">⚡ Vector Database</div>
            <div style="font-size:0.83rem; color:var(--muted);">Swap numpy cosine with FAISS or Pinecone
            for ANN search across billions of embeddings in milliseconds.</div>
        </div>
        <div>
            <div style="color:#fff; font-weight:600; margin-bottom:0.4rem;">🔄 Real-time Pipelines</div>
            <div style="font-size:0.83rem; color:var(--muted);">Pub/Sub + Cloud Run Jobs for async ingestion.
            Vertex AI for scalable model inference. Redis for embedding cache.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; margin-top:1.5rem; font-family:'Share Tech Mono',monospace;
            font-size:0.72rem; color:var(--muted);">
    Digital Asset Protection System · MVP · Built with FastAPI + Streamlit + MobileNetV2 + Stegano
</div>
""", unsafe_allow_html=True)