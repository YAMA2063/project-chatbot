from fastapi import FastAPI, Form, UploadFile, File, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from rag import get_context, sync_vectordb, VECTOR_DB_PATH
import os, shutil, smtplib, random, time, hashlib, json, uuid, secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, set_key
import pdfplumber, re
from groq import Groq
import jwt                         # PyJWT
import bcrypt                      # bcrypt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime, timezone, timedelta
try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("[WARN] google-genai tidak terinstall. Gemini dinonaktifkan.")

load_dotenv()

# ─── RATE LIMITER ───
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title="Chatbot RAG Gunadarma", version="2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/admin.html")
async def serve_admin():
    return FileResponse("admin.html")

# ─── MONITORING & METRICS TRACKER (Latency p50/p95/p99) ───
_app_start_time = time.time()
_request_latencies = []
_total_requests = 0
_total_errors = 0
_MAX_LATENCY_SAMPLES = 500

def get_latency_percentiles():
    if not _request_latencies:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "avg_ms": 0.0, "samples": 0}
    sorted_l = sorted(_request_latencies)
    n = len(sorted_l)
    def p(pct):
        idx = min(int(n * pct), n - 1)
        return round(sorted_l[idx], 2)
    return {
        "p50_ms": p(0.50),
        "p95_ms": p(0.95),
        "p99_ms": p(0.99),
        "avg_ms": round(sum(sorted_l) / n, 2),
        "samples": n
    }

@app.middleware("http")
async def monitor_latency_middleware(request: Request, call_next):
    global _total_requests, _total_errors
    start_t = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_t) * 1000
        _total_requests += 1
        _request_latencies.append(duration_ms)
        if len(_request_latencies) > _MAX_LATENCY_SAMPLES:
            _request_latencies.pop(0)
        return response
    except Exception as e:
        _total_errors += 1
        raise e

@app.get("/health")
async def health_check():
    vectordb_ready = os.path.exists(VECTOR_DB_PATH)
    manifest_file = os.path.join(VECTOR_DB_PATH, "index_manifest.json")
    doc_count = 0
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                doc_count = len(json.load(f))
        except Exception:
            pass

    return {
        "status": "healthy",
        "service": "Chatbot RAG Gunadarma v2.0",
        "uptime_seconds": round(time.time() - _app_start_time, 1),
        "vectordb": {
            "status": "ready" if vectordb_ready else "not_initialized",
            "indexed_documents": doc_count
        },
        "llm": {
            "provider": _LLM_PROVIDER,
            "gemini_active_keys": len(_GEMINI_KEYS),
            "gemini_model": _GEMINI_MODEL,
            "has_groq": bool(os.getenv("GROQ_API_KEY"))
        },
        "latency": get_latency_percentiles(),
        "traffic": {
            "total_requests": _total_requests,
            "total_errors": _total_errors
        }
    }

# ─── GROQ CLIENT ───
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─── GEMINI CLIENT (rotasi 3 key) ───
_GEMINI_KEYS = [
    k for k in [
        os.getenv("GEMINI_API_KEY_1", ""),
        os.getenv("GEMINI_API_KEY_2", ""),
        os.getenv("GEMINI_API_KEY_3", ""),
    ] if k
]
_gemini_key_index = 0   # Pointer rotasi key aktif

# Gemini 3 Model configuration & cascade
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-3.5-flash")
_GEMINI_MODELS = list(dict.fromkeys([
    _GEMINI_MODEL,
    "models/gemini-3.8-flash",
    "models/gemini-3.1-flash-lite",
    "models/gemini-3-flash-preview",
]))

def _get_gemini_client():
    """Buat Gemini client dengan key aktif."""
    if not HAS_GEMINI or not _GEMINI_KEYS:
        return None
    key = _GEMINI_KEYS[_gemini_key_index % len(_GEMINI_KEYS)]
    return google_genai.Client(api_key=key)

def _rotate_gemini_key():
    """Putar ke key berikutnya jika kena rate limit."""
    global _gemini_key_index
    _gemini_key_index = (_gemini_key_index + 1) % len(_GEMINI_KEYS)
    print(f"[Gemini 3] Rotasi ke key #{_gemini_key_index + 1}")

def _gemini_reform_query(system_content: str, pertanyaan_asli: str):
    """Query transformation menggunakan Gemini 3 dengan rotasi key dan model fallback."""
    if not HAS_GEMINI or not _GEMINI_KEYS:
        return None
    prompt = (system_content + "\n\nPertanyaan: " + pertanyaan_asli +
              '\n\nBerikan output JSON saja: {"query": "..."}')
    for m in _GEMINI_MODELS:
        for attempt in range(len(_GEMINI_KEYS)):
            try:
                gem_client = _get_gemini_client()
                if gem_client is None:
                    return None
                gem_resp = gem_client.models.generate_content(
                    model=m,
                    contents=prompt,
                )
                raw_text = (gem_resp.text or "").strip()
                json_match = re.search(r'\{.*?"query".*?\}', raw_text, re.DOTALL)
                if json_match:
                    raw_text = json_match.group(0)
                print(f"[Gemini 3 ({m})] perbaiki_pertanyaan OK: {raw_text[:60]}")
                return raw_text
            except Exception as gem_e:
                gem_err = str(gem_e).lower()
                if "quota" in gem_err or "429" in gem_err or "rate" in gem_err:
                    _rotate_gemini_key()
                    continue
                elif "503" in gem_err:
                    print(f"[Gemini 503 ({m})] sedang sibuk, coba model lain...")
                    break
                print(f"[ERROR Gemini perbaiki_pertanyaan ({m})] {gem_e}")
                break
    return None

def _gemini_stream_answer(system_content: str, question: str):
    """Streaming jawaban menggunakan Gemini 3 dengan rotasi key dan model fallback."""
    if not HAS_GEMINI or not _GEMINI_KEYS:
        return
    full_prompt = system_content + "\n\nPertanyaan user: " + question
    for m in _GEMINI_MODELS:
        for attempt in range(len(_GEMINI_KEYS)):
            try:
                gem_client = _get_gemini_client()
                if gem_client is None:
                    return
                gem_response = gem_client.models.generate_content_stream(
                    model=m,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=1024,
                    ),
                )
                yielded_any = False
                for chunk in gem_response:
                    if chunk.text:
                        yielded_any = True
                        yield chunk.text
                if yielded_any:
                    return
            except Exception as gem_e:
                gem_err = str(gem_e).lower()
                if "quota" in gem_err or "429" in gem_err or "rate" in gem_err:
                    _rotate_gemini_key()
                    continue
                elif "503" in gem_err:
                    print(f"[Gemini 503 ({m})] sedang sibuk, coba model/key lain...")
                    break
                print(f"[ERROR Gemini stream_answer ({m})] {gem_e}")
                break

# LLM_PROVIDER: "groq" | "gemini" | "auto" (default: auto)
_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
print(f"[LLM] Provider: {_LLM_PROVIDER} | Groq: OK | Gemini 3 ({_GEMINI_MODEL}): {len(_GEMINI_KEYS)} keys")

# ─── CORS (dibatasi ke origin yang dikonfigurasi) ───
_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─── SECURITY RESPONSE HEADERS ───
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response

DATA_FOLDER = "./data preprocessing"
ENV_FILE = "./.env"

# ─── OTP STORE: {email: {"otp": str, "expires": float, "attempts": int}} ───
otp_store: dict = {}

# ─── JWT BLACKLIST (revoked jti) — in-memory set ───
_jwt_blacklist: set = set()

# ─── KONSTANTA JWT ───
_JWT_SECRET    = os.getenv("JWT_SECRET", secrets.token_hex(32))  # fallback random tiap restart
_JWT_ALGO      = "HS256"
_JWT_EXP_HOURS = 8
_OTP_MAX_TRIES = 3

# ─── HELPER: PASSWORD BCRYPT ───

def hash_password_bcrypt(password: str) -> str:
    """Hash password dengan bcrypt (disimpan di .env sebagai ADMIN_PASSWORD_HASH)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str) -> bool:
    """Verifikasi password terhadap hash bcrypt ATAU plain text (backward-compat)."""
    stored_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    # Backward-compat: plain text (harus segera di-migrate)
    return password == os.getenv("ADMIN_PASSWORD", "")

# ─── HELPER: JWT ───

def generate_jwt(username: str) -> str:
    """Buat JWT HS256 dengan expiry 8 jam dan unique jti."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=_JWT_EXP_HOURS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)

def decode_jwt(token: str) -> dict:
    """Decode dan validasi JWT. Raise ValueError jika tidak valid."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token sudah kedaluwarsa, silakan login ulang.")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token tidak valid: {e}")
    if payload.get("jti") in _jwt_blacklist:
        raise ValueError("Token telah di-revoke (logout).")
    return payload

def revoke_jwt(token: str):
    """Tambahkan jti ke blacklist saat logout."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO],
                             options={"verify_exp": False})
        _jwt_blacklist.add(payload.get("jti", ""))
    except Exception:
        pass

security = HTTPBearer(auto_error=False)

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    try:
        decode_jwt(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return True

def kirim_email_otp(email_tujuan: str, kode_otp: str):
    sender = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = email_tujuan
    msg["Subject"] = "Kode OTP Reset Password - Admin Chatbot Gunadarma"

    body = f"""
Halo Admin,

Kode OTP untuk reset password Anda adalah:

  [ {kode_otp} ]

Kode ini berlaku selama 10 menit.

Jika Anda tidak meminta reset password, abaikan email ini.

— Sistem Chatbot Universitas Gunadarma
"""
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, email_tujuan, msg.as_string())

# ─── ENDPOINT USER ───

def perbaiki_pertanyaan(pertanyaan_asli: str, riwayat_teks: str = "") -> str:
    system_content = """Tugasmu mengekstrak kata inti (search query) dari pertanyaan mahasiswa untuk mencari dokumen di database Universitas Gunadarma.

ATURAN MUTLAK (IKUTI DENGAN SANGAT TEGAS):
1. KAMU HARUS MENGELUARKAN OUTPUT DALAM FORMAT JSON SEPERTI INI: {"query": "kata kuncinya di sini"}
2. DILARANG KERAS MENJAWAB PERTANYAAN USER ATAU MEMBERIKAN PENJELASAN. OUTPUT HANYA BOLEH JSON!
3. EKSTRAK INTI PERTANYAAN: Jika pertanyaan tidak jelas, ambil kata benda atau subjek utamanya saja (Maksimal 5 kata).
   - Tambahkan jurusan di belakangnya: KA -> S1 Sistem Informasi, IA -> S1 Informatika, dsb.
   - Contoh: "1KA28" -> "1KA28 S1 Sistem Informasi"
   - Contoh: "ka28" -> "KA28 S1 Sistem Informasi"
4. PENCARIAN DOSEN WALI: Jika menanyakan wali kelas, gunakan format: "Dosen Wali Kelas [Kode Kelas]".
   - Contoh: "siapa wali kelas 1KA01" -> "Dosen Wali Kelas 1KA01"
5. NAMA ORANG = DOSEN: Jika user menyebut nama orang (misal "bu lulu", "pak joko", "nurlintang"), keluarkan HANYA nama orang tersebut tanpa embel-embel apapun!
   - Contoh: "bu lulu ngajar apa" -> "Lulu"
   - Contoh: "nurlintang" -> "Nurlintang"
   - Contoh: "pak joko" -> "Joko"
6. JADWAL KULIAH / MATKUL: Jika bertanya matkul suatu kelas, cukup keluarkan kelas dan jurusannya.
   - Contoh: "jadwal 1ka01" -> "Jadwal 1KA01 S1 Sistem Informasi"
   - Contoh: "1ka28 belajar apa" -> "Mata Kuliah 1KA28 S1 Sistem Informasi"
7. DOSEN PENGAJAR: Jika bertanya dosen matkul tertentu, gunakan "Koordinator Mata Kuliah [Nama Matkul]".
8. TERJEMAHAN GAUL: Hapus kata tanya gaul seperti "syp", "yak", "dong", "ngab", "min". 
9. PENCARIAN NAMA MAHASISWA: Jika user menyebut nama mahasiswa, HANYA keluarkan nama mahasiswa tersebut! DILARANG menambahkan kata "Dosen Pengajar", "Pembimbing", dll.
   - Contoh: "mira trisnatul diajar siapa" -> "Mira Trisnatul"

CONTOH KASUS:
User: "dosen wali 1ka01 siapa"
Output: {"query": "Dosen Wali Kelas 1KA01"}
User: "1ka28"
Output: {"query": "1KA28 S1 Sistem Informasi"}
User: "ka28"
Output: {"query": "KA28 S1 Sistem Informasi"}
User: "kalau ka05"
Output: {"query": "KA05 S1 Sistem Informasi"}
User: "bu lulu"
Output: {"query": "Lulu"}
User: "mira trisnatul npm berapa"
Output: {"query": "Mira Trisnatul"}
"""
    if riwayat_teks:
        system_content += f"""\n
PERHATIAN - KONTEKS RIWAYAT CHAT:
Di bawah ini adalah riwayat percakapan sebelumnya. Jika pertanyaan terbaru tidak lengkap atau merupakan kalimat sambungan (misal hanya menyebut "kalau kelas 1KA02?"), kamu WAJIB melihat riwayat untuk mengetahui topik apa yang sedang dibicarakan (misalnya sebelumnya bertanya tentang "dosen wali"). 
Lalu, GABUNGKAN topik tersebut dengan pertanyaan terbaru sehingga menjadi query pencarian yang utuh (misal: "Dosen wali kelas 1KA02 S1 Sistem Informasi").

PERINGATAN KERAS: MESKIPUN ADA RIWAYAT, KAMU TETAP DILARANG MENJAWAB PERTANYAAN USER! KELUARKAN HANYA OBJEK JSON: {{"query": "..."}}. JIKA USER BERTANYA SECARA KASUAL (MISAL: "lu bisa liat obrolan ga"), JANGAN PERNAH MENJAWAB "Maaf saya tidak bisa". BALAS DENGAN {{"query": "Tidak Relevan"}}.

=== RIWAYAT PERCAKAPAN ===
{riwayat_teks}
=========================
"""

    raw_query = None
    if _LLM_PROVIDER == "gemini":
        raw_query = _gemini_reform_query(system_content, pertanyaan_asli)
        if not raw_query:
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": pertanyaan_asli}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_query = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[ERROR GROQ fallback perbaiki_pertanyaan] {e}")
                return pertanyaan_asli
    else:
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": pertanyaan_asli}
                ],
                response_format={"type": "json_object"}
            )
            raw_query = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR GROQ perbaiki_pertanyaan] {e}")
            if _LLM_PROVIDER != "groq":
                raw_query = _gemini_reform_query(system_content, pertanyaan_asli)
            if not raw_query:
                return pertanyaan_asli
    
    # Parse JSON dan ambil value 'query'
    try:
        query_data = json.loads(raw_query)
        clean_query = query_data.get("query", "")
    except Exception:
        clean_query = raw_query
        
    # PEMBERSIHAN PAKSA (Anti AI Basa-Basi dan Anti Markdown)
    clean_query = clean_query.replace("Kata kunci:", "").replace("Query:", "").replace("\"", "").replace("'", "")
    clean_query = clean_query.replace("*", "").replace("`", "").replace("_", "")
    if clean_query.lower().startswith("baik,"): 
        clean_query = clean_query.split(",")[-1]
    
    # Jika masih ngeyel mengeluarkan kalimat panjang, potong paksa!
    if len(clean_query.split()) > 7:
        clean_query = " ".join(clean_query.split()[:7])
    
    return clean_query.strip()

def stream_answer(question: str, context: str, riwayat_teks: str = ""):
    # Truncate context to save tokens and prevent Groq's 8000 TPM limit
    if len(context) > 6000:
        context = context[:6000] + "\n...[TEKS DIPOTONG KARENA LIMIT]..."

    system_content = f"""Kamu adalah Asisten Kampus Gunadarma yang super ramah, asyik, dan suportif layaknya kakak tingkat (kating). Tujuan utamamu adalah membantu mahasiswa baru agar mereka TIDAK PERLU repot mencari informasi sendiri. Jawablah dengan SANGAT LUWES dan JANGAN KAKU seperti robot!

DOKUMEN REFERENSI (Bahan mutlak jawabanmu):
{context}

ATURAN MEMBACA DATA (ANTI HALUSINASI - SANGAT PENTING):
1. BACA TEKS DENGAN MATAMU! Jangan gunakan asumsi umum atau ingatan bawaanmu.
2. JIKA ADA DATA MAHASISWA/KELAS: Sebutkan SEMUANYA tanpa terkecuali! DILARANG KERAS merangkum dengan kata "misalnya", "contohnya", "antara lain", atau "dst.". Tuliskan saja format datanya langsung seperti ini: "Beliau membimbing mahasiswa: A, B, C, D, E, F." (Tulis semua namanya secara definitif sebagai fakta mutlak!)
3. JANGAN GAMPANG MENYERAH (TERUTAMA SOAL JADWAL): Jika user bertanya hal umum seperti "Jadwal kuliah semester ini?" dan di referensi HANYA ada info tanggal masuk kuliah (kalender akademik) atau tata cara mengecek jadwal di BAAK, JAWABLAH MENGGUNAKAN INFO TERSEBUT! Jangan beralasan data kosong hanya karena jadwal per-kelasnya belum rilis. Rangkum semua info kalender & jadwal yang kamu temukan!
4. JIKA DATANYA BENAR-BENAR KOSONG: Barulah kamu BOLEH membalas: "Wah, maaf banget, aku belum nemu info soal itu nih. Coba sebutin kelas atau matkul spesifik kamu ya!"

ATURAN MEMBACA RENTANG KELAS:
Jika dokumen menyebut "Berlaku untuk kelas [KODE]01 sampai [KODE]XX", maka semua kelas di antara rentang tersebut PASTI tercakup. Langsung jawab dengan daftar matkul yang ada tanpa bilang "tidak ada informasi spesifik".
Contoh: dokumen menyebut "Berlaku untuk kelas 2DA01 sampai 2DA02", lalu user tanya kelas 2DA01 → langsung berikan matkulnya karena 2DA01 ada dalam rentang tersebut.

ATURAN MENJAWAB (PANTANGAN Keras):
1. LARANGAN MENYURUH CEK SENDIRI: Jangan menyuruh user "cek web" ATAU "tanya loket BAAK", KECUALI teks referensi secara eksplisit menyatakan bahwa informasi tersebut HANYA bisa dilihat di web BAAK Online atau Loket BAAK (seperti halnya "Jadwal Kuliah" atau "Jadwal Ujian"). Jika teks menyuruh ke BAAK, sampaikanlah dengan gaya kating (contoh: "Kalo jadwal kuliah sih biasanya diumumin langsung di web BAAK Online atau ditempel di mading kampus. Coba kamu cek ke sana ya!").
3. HANYA JAWAB DARI TOPIK YANG SAMA: Jika user bertanya tentang 'Wisuda', maka kamu HANYA boleh merangkum teks dari paragraf yang berjudul atau secara eksplisit membahas 'Wisuda'.
4. JANGAN MENGARANG BEBAS.
5. LINK HARUS RELEVAN: Jika di dalam teks referensi terdapat tautan (URL), berikan tautan tersebut HANYA JIKA tautan itu benar-benar berkaitan langsung dengan topik pertanyaan user. JANGAN sembarangan menyisipkan link dari paragraf/dokumen lain yang tidak nyambung!
6. JURUSAN MUTLAK: Jika user menanyakan mata kuliah untuk "Sistem Informasi", maka kamu HANYA boleh melihat data yang berlabel "Sistem Informasi" atau kelas berawalan "KA". JANGAN SEKALI-KALI menjawab dengan data "Informatika" (kelas IA), "Sistem Komputer" (kelas KB), atau "D3" jika yang ditanyakan S1, begitu juga sebaliknya!
7. PANTANGAN KATA (HARAM DIUCAPKAN): JANGAN PERNAH mengetik kata "dokumen", "referensi", "teks", "database", "sistem", "data", "catatan", ATAU nama file berakhiran ".txt"! DILARANG KERAS menyuruh user mencari di file "daftar_koordinator_matkul.txt" dsb. Sembunyikan identitas file-file tersebut (termasuk tag [Sumber: ...]) dari matamu! Jika Anda tidak tahu sesuatu, nyatakan sebagai fakta mutlak (contoh: "Beliau memang tidak mengajar matkul"), JANGAN beralasan "tidak ada di sistem"!
8. HINDARI MENGULANG SLANG USER SECARA HARFIAH: Pahami konteksnya dan langsung jawab nama dosennya!
9. ARTI NAMA FILE UNTUK JABATAN DOSEN (SANGAT PENTING): 
   - Teks berawalan [Sumber: daftar_dosen_kelas4.txt] berarti dosen itu adalah **Dosen Wali Kelas**, BUKAN dosen pengajar.
   - Teks berawalan [Sumber: daftar_dosen_pi.txt] berarti dosen itu adalah **Dosen Pembimbing PI**.
   - Teks berawalan [Sumber: daftar_koordinator_matkul.txt] berarti dosen itu adalah **Dosen Pengajar Matkul**.
11. JANGAN TERTUKAR NAMA DOSEN & MAHASISWA: Jika mencari dosen bernama "Lulu", teliti teksnya! Jika teks berbunyi "Nama: LULU AZMI, Dosen Pembimbing: WESTI", berarti Lulu adalah MAHASISWA. Jangan pernah laporkan mahasiswa bernama Lulu sebagai kelas bimbingan Bu Lulu!
12. LAPORKAN SEMUA PERAN (JANGAN ADA YANG TERLEWAT): Jika seorang dosen muncul di file PI dan juga di file Wali Kelas, SEBUTKAN KEDUANYA! Jangan pernah menyimpulkan "beliau bukan wali kelas" jika namanya jelas-jelas tercetak di [Sumber: daftar_dosen_kelas4.txt]!
13. CARA MENJAWAB JIKA DOSEN TIDAK MENGAJAR MATKUL: HARAM HUKUMNYA beralasan "tidak ada di sistem", "belum ada catatan", atau "dokumen tidak menyebutkan". Langsung nyatakan sebagai FAKTA mutlak bahwa dosen tersebut memang tidak mengajar matkul!
14. JIKA INFO SPESIFIK (TANGGAL) TIDAK ADA TAPI ADA ATURAN UMUM: Jangan langsung minta maaf! Kutip aturan umum tersebut (misal: "sesuai kalender akademik") dan jelaskan logika atau prasyaratnya berdasarkan dokumen!

ATURAN GAYA BAHASA:
1. PANTANGAN TERBESAR: JANGAN menggunakan kalimat birokrasi kaku! JANGAN mengulang pertanyaan user di awal kalimat. Langsung jawab intinya.
2. FORMAT MENGALIR (PENTING): JANGAN selalu memakai bullet points/nomor kaku! Jika infonya singkat, jawablah dalam bentuk paragraf naratif yang santai seperti orang mengobrol.
3. KETAT ANTI-HALUSINASI DETAIL: DILARANG KERAS menambahkan detail fiktif yang tidak ada di dokumen (seperti URL baak.gunadarma.ac.id, lokasi detail Gedung 3 Lantai 1, atau menyuruh WA dosen). HANYA sebutkan apa yang persis tertulis di dokumen referensi!
4. PARAFRASE SANTAI: Jangan copy-paste teks asli mentah-mentah! Ubah kata-kata kaku menjadi bahasa tongkrongan. 
   - Ubah frasa "Telah dinyatakan lulus" menjadi "Udah lulus".
   - Ubah segala kata "digandakan" atau "menggandakan" menjadi "di-print rangkap" atau "di-fotokopi".
5. Gunakan **bold** pada kata-kata penting agar mudah dibaca."""

    if riwayat_teks:
        system_content += f"\n\nRIWAYAT PERCAKAPAN (Untuk konteks referensi):\n{riwayat_teks}"

    if _LLM_PROVIDER == "gemini":
        gemini_success = False
        for chunk in _gemini_stream_answer(system_content, question):
            gemini_success = True
            yield chunk
        if not gemini_success:
            print("[Fallback] Gemini gagal, coba Groq...")
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    temperature=0.4,
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": question}
                    ],
                    stream=True
                )
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                print(f"[ERROR GROQ fallback stream_answer] {e}")
                yield "\n\n**Waduh, otak AI-nya lagi kepanasan (overload) atau limit hariannya sudah habis nih. Coba tunggu sekitar 15-20 menit lagi ya bro/sis!** 🚀"
        return

    # Default (auto atau groq): Coba Groq dulu
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            temperature=0.4,  # Ditingkatkan agar AI lebih santai dan tidak kaku
            messages=[
                {
                    "role": "system",
                    "content": system_content
                },
                {"role": "user", "content": question}
            ],
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"[ERROR GROQ stream_answer] {e}")
        # Fallback ke Gemini 3 jika Groq kena limit / error & provider bukan paksa Groq
        if _LLM_PROVIDER != "groq" and HAS_GEMINI and _GEMINI_KEYS:
            print("[Fallback] Groq gagal, coba Gemini 3...")
            gemini_success = False
            for chunk in _gemini_stream_answer(system_content, question):
                gemini_success = True
                yield chunk
            if gemini_success:
                return
        yield "\n\n**Waduh, otak AI-nya lagi kepanasan (overload) atau limit hariannya sudah habis nih. Coba tunggu sekitar 15-20 menit lagi ya bro/sis!** 🚀"

@app.post("/tanya-ai/")
async def tanya_ai(pertanyaan: str = Form(...), riwayat: str = Form(None)):
    print(f"\n{'='*60}")
    print(f"1. Pertanyaan Asli : {pertanyaan}")
    
    # Proses riwayat dari frontend
    riwayat_teks = ""
    print(f"   [DEBUG] RAW riwayat dari frontend: {riwayat}")
    if riwayat:
        try:
            riwayat_list = json.loads(riwayat)
            for msg in riwayat_list:
                role = "User" if msg.get("role") == "user" else "Asisten"
                # Bersihkan pesan loading bot jika tersangkut
                if msg.get('content') and msg.get('content') != "...":
                    riwayat_teks += f"{role}: {msg.get('content')}\n"
            if riwayat_teks:
                print(f"   [Riwayat lokal dimuat: {len(riwayat_list)} pesan]")
            else:
                print("   [Riwayat kosong setelah di-filter]")
        except Exception as e:
            print("Gagal memproses riwayat lokal:", e)

    pertanyaan_formal = perbaiki_pertanyaan(pertanyaan, riwayat_teks)
    
    # FALLBACK: Jika query kosong setelah pembersihan, gunakan pertanyaan asli
    if not pertanyaan_formal.strip():
        pertanyaan_formal = pertanyaan
        print(f"2. Query Pencarian : {pertanyaan_formal} [FALLBACK - query kosong, pakai pertanyaan asli]")
    else:
        print(f"2. Query Pencarian : {pertanyaan_formal}")
    
    # Deteksi jika di luar topik
    if pertanyaan_formal.strip() == "Tidak Relevan":
        async def stream_out_of_topic():
            yield "Maaf ya, aku cuma Asisten Akademik Kampus Gunadarma. Aku cuma bisa bantu jawab pertanyaan seputar jadwal kuliah, KRS, ujian, administrasi, dan info kampus lainnya. Ada yang bisa dibantu soal kampus?"
        return StreamingResponse(stream_out_of_topic(), media_type="text/plain")
        
    context, sources = get_context(pertanyaan_formal)
    print(f"3. Konteks dari DB : {context[:300]}...\n[...teks dipotong untuk log...]")
    print(f"   Sumber ditemukan: {sources}")
    print(f"{'='*60}")

    async def stream_with_log():
        full_answer = ""
        for chunk in stream_answer(pertanyaan, context, riwayat_teks):
            full_answer += chunk
            yield chunk
        
        # Tambahkan sitasi sumber di akhir jawaban
        if sources:
            source_badges = "  ".join([f"`{s}`" for s in sources])
            citation = f"\n\n---\n📄 **Sumber Dokumen:** {source_badges}"
            full_answer += citation
            yield citation
        
        print(f"\n4. Jawaban AI      : {full_answer}")
        print(f"{'='*60}\n")

    return StreamingResponse(stream_with_log(), media_type="text/plain")

# ─── ENDPOINT ADMIN ───

@app.post("/admin/login")
@limiter.limit("5/minute")        # Max 5 percobaan login per menit per IP
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    stored_username = os.getenv("ADMIN_USERNAME", "")
    # Verifikasi username + password (bcrypt-aware)
    if username == stored_username and verify_password(password):
        token = generate_jwt(username)
        return {"success": True, "token": token, "expires_in": f"{_JWT_EXP_HOURS}h"}
    # Delay kecil untuk mencegah timing attack
    time.sleep(0.5)
    raise HTTPException(status_code=401, detail="Username atau password salah")

@app.post("/admin/logout", dependencies=[Depends(get_current_admin)])
async def admin_logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Revoke JWT saat logout agar token tidak bisa dipakai lagi."""
    if credentials:
        revoke_jwt(credentials.credentials)
    return {"success": True, "message": "Logout berhasil. Token di-revoke."}

@app.get("/admin/dokumen", dependencies=[Depends(get_current_admin)])
async def list_dokumen():
    if not os.path.exists(DATA_FOLDER):
        return {"files": []}
    files = []
    for f in sorted(os.listdir(DATA_FOLDER)):
        if f.endswith(".txt"):
            size = os.path.getsize(os.path.join(DATA_FOLDER, f))
            files.append({"nama": f, "ukuran": f"{round(size/1024, 1)} KB"})
    return {"files": files}

@app.get("/admin/dokumen/baca/{nama_file}", dependencies=[Depends(get_current_admin)])
async def baca_dokumen(nama_file: str):
    """Membaca isi file teks dari folder data"""
    filepath = os.path.join(DATA_FOLDER, nama_file)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    if not nama_file.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Hanya file .txt yang dapat dibaca")
    # Cegah path traversal
    abs_data = os.path.realpath(DATA_FOLDER)
    abs_file = os.path.realpath(filepath)
    if not abs_file.startswith(abs_data):
        raise HTTPException(status_code=403, detail="Akses ditolak")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            isi = f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as f:
            isi = f.read()
    return {"success": True, "nama": nama_file, "isi": isi}

@app.post("/admin/upload", dependencies=[Depends(get_current_admin)])
async def upload_dokumen(file: UploadFile = File(...)):
    if not (file.filename.endswith(".txt") or file.filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Hanya file .txt atau .pdf yang diizinkan")
        
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        
    if file.filename.endswith(".txt"):
        filepath = os.path.join(DATA_FOLDER, file.filename)
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return {"success": True, "message": f"File '{file.filename}' berhasil diupload"}
        
    elif file.filename.endswith(".pdf"):
        # Simpan file PDF sementara
        temp_pdf_path = os.path.join(DATA_FOLDER, file.filename)
        with open(temp_pdf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        try:
            all_content = []
            with pdfplumber.open(temp_pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_content = f"--- Halaman {page_num + 1} ---\n\n"
                    
                    # 1. Ekstraksi Tabel
                    tables = page.extract_tables()
                    if tables:
                        page_content += "[EKSTRAKSI TABEL DETEKSI]\n"
                        for table in tables:
                            for row_idx, row in enumerate(table):
                                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                                row_md = "| " + " | ".join(clean_row) + " |"
                                page_content += row_md + "\n"
                                if row_idx == 0:
                                    page_content += "|" + "|".join(["---"] * len(clean_row)) + "|\n"
                            page_content += "\n"
                            
                    # 2. Ekstraksi Teks (Layout Mode)
                    text = page.extract_text(layout=True)
                    if text:
                        page_content += "[EKSTRAKSI TEKS]\n"
                        page_content += text + "\n"
                        
                    # Bersihkan noise sementara
                    if page_content:
                        page_content = re.sub(r'^\s*\d+\s*$', '', page_content, flags=re.MULTILINE)
                        page_content = re.sub(r'\n{3,}', '\n\n', page_content).strip()
                        
                        # 3. Kirim teks mentah halaman ini ke Groq LLM untuk direstrukturisasi menjadi naratif
                        prompt_system = (
                            "Kamu adalah asisten AI akademik yang ahli mengkonversi data. "
                            "Tugasmu merestrukturisasi teks mentah dan tabel markdown hasil ekstraksi PDF berikut menjadi teks naratif atau list (daftar) yang koheren, rapi, dan mudah dibaca oleh manusia/algoritma RAG. "
                            "ATURAN MUTLAK:\n"
                            "1. DILARANG KERAS memberikan basa-basi, perkenalan, atau kalimat pengantar seperti 'Berikut adalah...'. LANGSUNG berikan hasil teksnya di baris pertama!\n"
                            "2. DILARANG KERAS MENGHAPUS/MENGURANGI INFORMASI (seperti angka SKS, jam, hari, nama dosen, NIDN, dll). Semuanya WAJIB dipertahankan.\n"
                            "3. Jika ada data berbentuk matriks tabel, ubah menjadi bentuk list berurutan.\n"
                            "4. DILARANG KERAS menggunakan format markdown (seperti bold, italic, heading). Output harus plain text murni!\n"
                            "5. SIMBOL BINTANG HARGA MATI: Jika di teks asli ada tanda bintang tunggal/ganda/tiga (*, **, ***), PERTAHANKAN TANDA BINTANG TERSEBUT APA ADANYA di posisi aslinya. JANGAN ubah atau ganti tanda bintang (*) menjadi kata penjelasannya di dalam list, dan JANGAN ubah menjadi tanda strip (-). Biarkan tanda bintang tetap tertulis sebagai bintang!\n"
                            "6. Hanya keluarkan SATU versi output final."
                        )
                        try:
                            # Coba pakai model utama yang paling cepat
                            response = client.chat.completions.create(
                                model="openai/gpt-oss-20b",
                                messages=[
                                    {"role": "system", "content": prompt_system},
                                    {"role": "user", "content": f"Teks mentah:\n\n{page_content}"}
                                ]
                            )
                        except Exception as e:
                            error_msg = str(e).lower()
                            # Jika kena limit, otomatis pindah ke model cadangan (tanpa ngasih tau user ada error)
                            if "rate limit" in error_msg or "429" in error_msg:
                                print(f"[Info] Halaman {page_num + 1} beralih ke model llama-3.3-70b-versatile karena limit.")
                                response = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[
                                        {"role": "system", "content": prompt_system},
                                        {"role": "user", "content": f"Teks mentah:\n\n{page_content}"}
                                    ]
                                )
                            else:
                                raise e # Lempar error asli jika bukan masalah limit
                        
                        # Ambil hasil dan gabungkan
                        hasil_llm = response.choices[0].message.content.strip()
                        all_content.append(f"--- Bagian {page_num + 1} ---\n" + hasil_llm)
                        
                        # Beri jeda sepersekian detik antar halaman untuk mencegah Rate Limit
                        time.sleep(1)
            
            # Simpan hasil akhir ke .txt langsung ke folder utama
            final_text = "\n\n".join(all_content)
            txt_filename = file.filename.replace(".pdf", ".txt")
            
            if not os.path.exists(DATA_FOLDER):
                os.makedirs(DATA_FOLDER)
                
            txt_filepath = os.path.join(DATA_FOLDER, txt_filename)
            
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(final_text)
                
            # Hapus PDF sementara
            os.remove(temp_pdf_path)
            
            return {"success": True, "message": f"File '{file.filename}' berhasil diekstrak dengan AI dan disimpan langsung ke '{DATA_FOLDER}' sebagai '{txt_filename}'. Jangan lupa klik Sinkronisasi!"}
            
        except Exception as e:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            raise HTTPException(status_code=500, detail=f"Gagal memproses PDF: {str(e)}")

@app.delete("/admin/dokumen/{nama_file:path}", dependencies=[Depends(get_current_admin)])
async def hapus_dokumen(nama_file: str):
    nama_file = nama_file.strip().strip("'").strip('"') # Bersihkan nama file dari kutip/spasi nyasar
    filepath = os.path.join(DATA_FOLDER, nama_file)
    if not os.path.exists(filepath):
        # Jika tidak ditemukan, coba cari nama aslinya
        raise HTTPException(status_code=404, detail=f"File tidak ditemukan: {nama_file}")
    os.remove(filepath)
    return {"success": True, "message": f"File '{nama_file}' berhasil dihapus"}

@app.post("/admin/sinkronisasi", dependencies=[Depends(get_current_admin)])
async def sinkronisasi_vektor():
    try:
        start_time = time.time()
        # Incremental sync: hanya proses file yang baru/berubah/dihapus
        _, stats = sync_vectordb(force_rebuild=False)
        end_time = time.time()
        
        elapsed_seconds = int(end_time - start_time)
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        time_str = f"{minutes} menit {seconds} detik" if minutes > 0 else f"{seconds} detik"
        
        total_changed = stats['added'] + stats['updated'] + stats['deleted']
        if total_changed == 0:
            detail = "Semua file sudah sinkron, tidak ada perubahan."
        else:
            parts = []
            if stats['added'] > 0: parts.append(f"{stats['added']} file baru")
            if stats['updated'] > 0: parts.append(f"{stats['updated']} file diperbarui")
            if stats['deleted'] > 0: parts.append(f"{stats['deleted']} file dihapus")
            detail = ", ".join(parts)
        
        return {"success": True, "message": f"Sinkronisasi selesai dalam {time_str}! {detail}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal sinkronisasi: {str(e)}")

@app.post("/admin/ganti-password", dependencies=[Depends(get_current_admin)])
async def ganti_password(password_lama: str = Form(...), password_baru: str = Form(...)):
    if len(password_baru) < 8:
        raise HTTPException(status_code=400, detail="Password baru minimal 8 karakter")
    if not verify_password(password_lama):
        time.sleep(0.5)  # Anti brute-force
        raise HTTPException(status_code=401, detail="Password lama tidak sesuai")
    # Simpan sebagai bcrypt hash
    new_hash = hash_password_bcrypt(password_baru)
    set_key(ENV_FILE, "ADMIN_PASSWORD_HASH", new_hash)
    # Hapus plain-text password lama jika masih ada
    set_key(ENV_FILE, "ADMIN_PASSWORD", "")
    load_dotenv(override=True)
    return {"success": True, "message": "Password berhasil diubah (disimpan sebagai hash). Silakan login ulang."}

@app.post("/admin/kirim-otp")
@limiter.limit("3/minute")         # Mencegah OTP spam
async def kirim_otp(request: Request):
    email_tujuan = os.getenv("ADMIN_EMAIL", "")
    if not email_tujuan:
        raise HTTPException(status_code=500, detail="Email admin belum dikonfigurasi di .env")
    # Gunakan secrets.randbelow untuk OTP yang lebih aman
    kode = f"{secrets.randbelow(900000) + 100000}"
    otp_store[email_tujuan] = {
        "otp":     kode,
        "expires": time.time() + 600,  # 10 menit
        "attempts": 0,                  # Counter percobaan
    }
    try:
        kirim_email_otp(email_tujuan, kode)
        parts = email_tujuan.split("@")
        email_sensor = parts[0][:3] + "***@" + parts[1]
        return {"success": True, "message": f"Kode OTP telah dikirim ke {email_sensor}"}
    except Exception as e:
        otp_store.pop(email_tujuan, None)  # Cleanup jika kirim gagal
        raise HTTPException(status_code=500, detail=f"Gagal kirim email: {str(e)}")

@app.post("/admin/verifikasi-otp")
@limiter.limit("5/minute")
async def verifikasi_otp(request: Request, otp: str = Form(...), password_baru: str = Form(...)):
    if len(password_baru) < 8:
        raise HTTPException(status_code=400, detail="Password baru minimal 8 karakter")
    email_tujuan = os.getenv("ADMIN_EMAIL", "")
    data = otp_store.get(email_tujuan)
    if not data:
        raise HTTPException(status_code=400, detail="OTP tidak ditemukan. Minta kode baru.")
    if time.time() > data["expires"]:
        otp_store.pop(email_tujuan, None)
        raise HTTPException(status_code=400, detail="OTP sudah kedaluwarsa. Minta kode baru.")
    # Limit percobaan OTP
    data["attempts"] = data.get("attempts", 0) + 1
    if data["attempts"] > _OTP_MAX_TRIES:
        otp_store.pop(email_tujuan, None)
        raise HTTPException(status_code=429, detail=f"Terlalu banyak percobaan OTP. Minta kode baru.")
    # Gunakan compare_digest untuk mencegah timing attack
    if not secrets.compare_digest(otp.strip(), data["otp"]):
        raise HTTPException(status_code=400, detail=f"Kode OTP salah (percobaan {data['attempts']}/{_OTP_MAX_TRIES})")
    # OTP valid — simpan password baru sebagai bcrypt hash
    new_hash = hash_password_bcrypt(password_baru)
    set_key(ENV_FILE, "ADMIN_PASSWORD_HASH", new_hash)
    set_key(ENV_FILE, "ADMIN_PASSWORD", "")  # Hapus plain text lama
    load_dotenv(override=True)
    otp_store.pop(email_tujuan, None)
    return {"success": True, "message": "Password berhasil direset dengan hash aman. Silakan login ulang."}