"""
streamlit_app.py — Asisten AI Universitas Gunadarma (RAG v2.0)
=============================================================
Aplikasi Demo Cloud 24 Jam Non-Stop untuk GitHub Portfolio & Showcase.
100% Free Hosting via Streamlit Community Cloud (Snowflake).
"""

import os
import re
import glob
import time
import streamlit as st
from dotenv import load_dotenv

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Asisten AI Gunadarma",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Load Environment Variables
load_dotenv()

# Prioritas API Keys: dari st.secrets (jika di Cloud) atau dari .env lokal
def get_secret(key, default=""):
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

GEMINI_KEY_1 = get_secret("GEMINI_API_KEY_1", "")
GEMINI_KEY_2 = get_secret("GEMINI_API_KEY_2", "")
GEMINI_KEY_3 = get_secret("GEMINI_API_KEY_3", "")
GEMINI_KEYS = [k for k in [GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_3] if k]
GROQ_API_KEY = get_secret("GROQ_API_KEY", "")

# ─── INISIALISASI CORPUS BM25 (CACHED DI RAM HANYA ~20 MB) ───
@st.cache_resource(show_spinner="Menyiapkan basis data kampus Gunadarma...")
def load_rag_engine():
    data_folder = os.path.join(os.path.dirname(__file__), "data preprocessing")
    if not os.path.exists(data_folder):
        data_folder = "./data preprocessing"

    corpus_docs = []
    corpus_tokens = []
    
    # Import BM25
    try:
        from rank_bm25 import BM25Okapi
        has_bm25 = True
    except ImportError:
        has_bm25 = False
        BM25Okapi = None

    for fpath in glob.glob(os.path.join(data_folder, "*.txt")):
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Split jadi paragraph atau chunk ~600 karakter
                paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
                if not paragraphs:
                    paragraphs = [content[:1000]]
                for p in paragraphs:
                    corpus_docs.append({"source": fname, "text": p})
                    if has_bm25:
                        tokens = re.findall(r'\w+', p.lower())
                        corpus_tokens.append(tokens)
        except Exception:
            pass

    bm25_model = BM25Okapi(corpus_tokens) if (has_bm25 and corpus_tokens) else None
    return corpus_docs, bm25_model, data_folder

corpus_docs, bm25_model, data_folder = load_rag_engine()

# ─── PENCARIAN KONTEKS (EXACT MATCH REGEX + BM25) ───
def search_context(question: str):
    keyword = question.lower().strip()
    context_chunks = []
    sources = set()

    # 1. Exact Match Regex (Kode Kelas: 1ka01, 3ia01, dll)
    class_codes = re.findall(r'\b[1-4]?[a-z]{2}\d{2}\b', keyword)
    if class_codes and os.path.exists(data_folder):
        for fpath in glob.glob(os.path.join(data_folder, "*daftar_dosen_kelas*.txt")):
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if any(code in line.lower() for code in class_codes):
                            context_chunks.append(f"[Dosen Wali Kelas] {line.strip()}")
                            sources.add(fname)
            except Exception:
                pass

    # 2. Exact Match Nama Dosen / Matkul jika query pendek
    if len(keyword.split()) <= 4 and os.path.exists(data_folder):
        for fpath in glob.glob(os.path.join(data_folder, "*.txt")):
            fname = os.path.basename(fpath)
            if any(k in fname for k in ["dosen", "jadwal", "matkul", "rps"]):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if re.search(r'\b' + re.escape(keyword) + r'\b', line.lower()):
                                context_chunks.append(f"[Sumber: {fname}] {line.strip()}")
                                sources.add(fname)
                except Exception:
                    pass

    # 3. BM25 Semantic Ranking
    if bm25_model:
        query_tokens = re.findall(r'\w+', keyword)
        if query_tokens:
            scores = bm25_model.get_scores(query_tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
            for idx in top_indices:
                if scores[idx] > 0.5:
                    doc = corpus_docs[idx]
                    context_chunks.append(f"[Sumber: {doc['source']}] {doc['text']}")
                    sources.add(doc['source'])

    combined_context = "\n\n".join(context_chunks[:15])
    return combined_context, list(sources)

# ─── GENERATE JAWABAN MENGGUNAKAN GEMINI / GROQ ───
def generate_ai_response(prompt: str, context: str):
    system_prompt = f"""Kamu adalah Asisten Kampus Gunadarma yang super ramah, asyik, dan suportif layaknya kakak tingkat (kating).
Gunakan informasi resmi dari Gunadarma berikut untuk menjawab:

REFERENSI RESMI:
{context}

ATURAN:
1. Jawab dengan bahasa Indonesia yang ramah, sopan, dan jelas.
2. Jika ada informasi dosen, kelas, jadwal, atau tanggal penting, sebutkan secara lengkap dan jelas.
3. Jangan menyuruh user cari sendiri kecuali referensi eksplisit menyebut harus cek loket/web BAAK.
4. Jika tidak ada info sama sekali di referensi, sampaikan dengan jujur dan ramah."""

    # Coba Google Gemini terlebih dahulu
    if GEMINI_KEYS:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_KEYS[0])
            full_prompt = f"{system_prompt}\n\nPertanyaan Mahasiswa: {prompt}"
            response = client.models.generate_content(
                model="models/gemini-2.5-flash",
                contents=full_prompt,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            # Fallback ke key berikutnya jika ada
            if len(GEMINI_KEYS) > 1:
                try:
                    client = genai.Client(api_key=GEMINI_KEYS[1])
                    full_prompt = f"{system_prompt}\n\nPertanyaan Mahasiswa: {prompt}"
                    response = client.models.generate_content(
                        model="models/gemini-2.5-flash",
                        contents=full_prompt,
                    )
                    if response and response.text:
                        return response.text
                except Exception:
                    pass

    # Fallback ke Groq Llama 3.3 70B
    if GROQ_API_KEY:
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_API_KEY)
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Maaf, server AI sedang mengalami antrean. Silakan coba sesaat lagi ({e})."

    return "Konfigurasi API Key belum diset. Pastikan GEMINI_API_KEY atau GROQ_API_KEY tersedia."

# ─── TAMPILAN APLIKASI (UI) ───
st.markdown("""
<style>
    .header-box {
        text-align: center;
        padding: 1.5rem 1rem;
        background: linear-gradient(135deg, #4A154B 0%, #2E0854 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(74, 21, 75, 0.25);
    }
    .header-box h1 { color: #FFD700; margin: 0; font-size: 1.8rem; }
    .header-box p { color: #E0E0E0; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
    .badge-source {
        background-color: #f0f2f6;
        color: #4A154B;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #d0d7de;
        display: inline-block;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1>🏛️ Asisten AI Universitas Gunadarma</h1>
    <p>Sistem RAG v2.0 • Tanya Jadwal, Dosen Wali, RPS, & Informasi Akademik Resmi</p>
</div>
""", unsafe_allow_html=True)

# Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Aku Asisten AI Universitas Gunadarma 🎓. Ada yang bisa aku bantu seputar jadwal kuliah, dosen pembimbing, RPS, atau kalender akademik?"}
    ]

# Tampilkan Riwayat Obrolan
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            sources_html = " ".join([f"<span class='badge-source'>📄 {s}</span>" for s in msg["sources"]])
            st.markdown(f"<div style='margin-top: 8px;'><b>Sumber Resmi:</b><br>{sources_html}</div>", unsafe_allow_html=True)

# Input Chat
if prompt := st.chat_input("Tanyakan sesuatu ke Asisten AI Gunadarma..."):
    # Tampilkan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Proses respons asisten
    with st.chat_message("assistant"):
        with st.spinner("Mencari dokumen resmi & menyusun jawaban..."):
            context, sources = search_context(prompt)
            answer = generate_ai_response(prompt, context)
            st.markdown(answer)
            if sources:
                sources_html = " ".join([f"<span class='badge-source'>📄 {s}</span>" for s in sources])
                st.markdown(f"<div style='margin-top: 8px;'><b>Sumber Resmi:</b><br>{sources_html}</div>", unsafe_allow_html=True)
                
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })
