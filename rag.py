"""
rag.py — RAG Engine v2.0 (Upgraded)
====================================
Fitur baru:
- Incremental Indexing (upsert/delete per dokumen, tanpa rebuild total)
- Metadata-Aware Chunking (prodi, kategori, jenjang per chunk)
- Hybrid Search: BM25 Sparse + Dense Vector + Reciprocal Rank Fusion (RRF)
- Source Citation Tracking (provenance)

Upgrade dari versi skripsi oleh Muhammad Thufeil Putrayama (11122006)
"""

import os
import re
import json
import hashlib
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# BM25 — graceful import (tidak crash jika belum terinstall)
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    print("[⚠️ Warning] rank-bm25 belum terinstall. Jalankan: pip install rank-bm25")

load_dotenv()

# ─── KONFIGURASI PATH ───
VECTOR_DB_PATH = "./vectordb"
DATA_FOLDER = "./data preprocessing"
MANIFEST_PATH = os.path.join(VECTOR_DB_PATH, "index_manifest.json")

# ─── SINGLETON INSTANCES ───
_vectordb_instance = None
_bm25_instance = None
_bm25_corpus = []       # List teks mentah seluruh chunks
_bm25_metadata = []     # List metadata dict per chunk


# ═══════════════════════════════════════════════════════════════
#  UTILITAS: Klasifikasi Metadata, Hashing, Manifest
# ═══════════════════════════════════════════════════════════════

def classify_document(filename):
    """
    Ekstrak metadata (kategori, prodi, jenjang) dari pola nama file secara otomatis.
    Metadata ini disimpan bersama setiap chunk di vector database.
    """
    fn = filename.lower()
    meta = {"source": filename, "kategori": "umum", "prodi": "", "jenjang": ""}

    # ── Deteksi Kategori ──
    if any(k in fn for k in ["jadwal_kuliah", "jadwal_uas", "jadwal_ujian", "dataset_jadwal"]):
        meta["kategori"] = "jadwal"
    elif "daftar_dosen_kelas" in fn:
        meta["kategori"] = "dosen_wali"
    elif "daftar_dosen_pi" in fn:
        meta["kategori"] = "dosen_pi"
    elif "daftar_koordinator_matkul" in fn:
        meta["kategori"] = "dosen_matkul"
    elif "daftar mata kuliah" in fn:
        meta["kategori"] = "mata_kuliah"
    elif any(k in fn for k in ["daftar_rps", "informasi_rps", "informasi_kontak_rps"]):
        meta["kategori"] = "rps"
    elif fn.startswith("profil_"):
        meta["kategori"] = "profil"
    elif any(k in fn for k in ["berita", "pengumuman"]):
        meta["kategori"] = "berita"
    elif any(fn.startswith(k) for k in ["buku pedoman", "materi", "laporan"]):
        meta["kategori"] = "pedoman"
    elif any(k in fn for k in [
        "formulir", "daftar ulang", "daftar sidang", "krs", "aktivasi",
        "blanko", "surat keterangan", "skpi", "wisuda", "ganti password",
        "pengecekan nilai", "email", "perpustakaan", "portofolio",
        "kalender", "akademik", "panduan", "pengurusan", "dataset_dokumen",
        "fakultas_dan_jurusan",
    ]):
        meta["kategori"] = "administrasi"

    # ── Deteksi Prodi (dari spesifik ke umum, agar "akuntansi komputer" tidak ke-match "akuntansi") ──
    prodi_map = [
        ("akuntansi komputer", "Akuntansi Komputer"),
        ("manajemen informatika", "Manajemen Informatika"),
        ("manajemen keuangan", "Manajemen Keuangan"),
        ("manajemen pemasaran", "Manajemen Pemasaran"),
        ("teknik komputer", "Teknik Komputer"),
        ("teknik sipil", "Teknik Sipil"),
        ("teknik mesin", "Teknik Mesin"),
        ("teknik elektro", "Teknik Elektro"),
        ("teknik industri", "Teknik Industri"),
        ("teknik arsitektur", "Teknik Arsitektur"),
        ("desain interior", "Desain Interior"),
        ("ilmu komunikasi", "Ilmu Komunikasi"),
        ("ekonomi syariah", "Ekonomi Syariah"),
        ("sastra inggris", "Sastra Inggris"),
        ("sastra tiongkok", "Sastra Tiongkok"),
        ("sistem informasi", "Sistem Informasi"),
        ("sistem komputer", "Sistem Komputer"),
        ("informatika", "Informatika"),
        ("akuntansi", "Akuntansi"),
        ("manajemen", "Manajemen"),
        ("psikologi", "Psikologi"),
        ("farmasi", "Farmasi"),
        ("kebidanan", "Kebidanan"),
        ("kedokteran", "Kedokteran"),
        ("pariwisata", "Pariwisata"),
        ("agroteknologi", "Agroteknologi"),
    ]
    for key, value in prodi_map:
        if key in fn:
            meta["prodi"] = value
            break

    # ── Deteksi Jenjang ──
    if any(k in fn for k in ["d3 ", "d3_", "d3-"]):
        meta["jenjang"] = "D3"
    elif any(k in fn for k in ["s1 ", "s1_", "s1-", "s1 -"]):
        meta["jenjang"] = "S1"

    return meta


def prettify_source(filename):
    """Mengubah nama file teknis menjadi nama sumber yang rapi untuk sitasi ke user."""
    name = filename.replace(".txt", "")

    # Peta nama file → nama sumber yang manusiawi
    pretty_map = {
        "daftar_dosen_kelas1": "Daftar Dosen Wali Kelas (Tingkat 1)",
        "daftar_dosen_kelas2": "Daftar Dosen Wali Kelas (Tingkat 2)",
        "daftar_dosen_kelas3": "Daftar Dosen Wali Kelas (Tingkat 3)",
        "daftar_dosen_kelas4": "Daftar Dosen Wali Kelas (Tingkat 4)",
        "daftar_dosen_pi": "Daftar Dosen Pembimbing PI",
        "daftar_koordinator_matkul": "Daftar Koordinator Mata Kuliah",
        "daftar_rps_master": "Rencana Pembelajaran Semester (RPS)",
        "jadwal_kuliah_master": "Jadwal Kuliah",
        "jadwal_uas_master": "Jadwal UAS",
        "jadwal_ujian": "Jadwal Ujian",
        "dataset_jadwal_ujian_utama": "Jadwal Ujian Utama",
        "berita_terbaru_baak": "Berita Terbaru BAAK",
        "kalender": "Kalender Akademik",
        "krs": "Panduan KRS",
        "akademik": "Informasi Akademik",
        "aktivasi": "Panduan Aktivasi",
        "dataset_dokumen_resmi": "Dokumen Resmi",
        "fakultas_dan_jurusan": "Daftar Fakultas & Jurusan",
        "informasi_rps": "Informasi RPS",
        "informasi_kontak_rps": "Kontak RPS",
        "panduan_jadwal_kuliah": "Panduan Jadwal Kuliah",
        "pengurusan_ujian_bentrok": "Pengurusan Ujian Bentrok",
        "pengumuman_bebas_keuangan": "Pengumuman Bebas Keuangan",
    }

    if name in pretty_map:
        return pretty_map[name]

    # Fallback: bersihkan nama file secara otomatis
    clean = name.replace("_", " ").replace("-", " ").title()
    # Perbaiki akronim yang salah kapital
    for abbr in ["S1", "D3", "BAAK", "RPS", "KRS", "PI", "UAS", "KTM", "DNS",
                  "SAP", "PPSPPT", "SKPI", "UKT", "NPM", "PA"]:
        clean = re.sub(rf'\b{abbr.title()}\b', abbr, clean)
    return clean


def compute_file_hash(filepath):
    """Hitung SHA-256 hash dari konten file untuk deteksi perubahan."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_manifest():
    """Muat manifest: file apa saja yang sudah terindeks, beserta hash dan chunk ID-nya."""
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def save_manifest(manifest):
    """Simpan manifest ke disk."""
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def get_embeddings():
    """Model embedding multilingual (singleton-safe karena HuggingFaceEmbeddings sudah caching)."""
    return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")


from collections import defaultdict


def _auto_bootstrap_manifest(vectordb):
    """
    Membangun manifest dari seluruh chunk yang sudah ada di Chroma tanpa re-embedding.
    Juga memperkaya metadata setiap chunk dengan kategori, prodi, dan jenjang.
    """
    manifest = {}
    try:
        count = vectordb._collection.count()
        if count == 0:
            return manifest

        print(f"[Sync] Auto-bootstrap manifest dari {count} chunk yang sudah ada...")
        all_data = vectordb.get(include=["metadatas"])
        ids = all_data.get("ids", [])
        metas = all_data.get("metadatas", [])

        file_chunks = defaultdict(list)
        update_ids = []
        update_metas = []

        for cid, meta in zip(ids, metas):
            raw_src = meta.get("source", "")
            fname = os.path.basename(raw_src.replace("\\", "/"))
            file_chunks[fname].append(cid)

            doc_meta = classify_document(fname)
            update_ids.append(cid)
            update_metas.append({
                "source": fname,
                "kategori": doc_meta["kategori"],
                "prodi": doc_meta["prodi"],
                "jenjang": doc_meta["jenjang"]
            })

        # Update metadata di Chroma secara batch
        for i in range(0, len(update_ids), 500):
            try:
                vectordb._collection.update(
                    ids=update_ids[i:i+500],
                    metadatas=update_metas[i:i+500]
                )
            except Exception:
                pass

        # Bangun manifest per file
        if os.path.exists(DATA_FOLDER):
            for fname in sorted(os.listdir(DATA_FOLDER)):
                if fname.endswith(".txt"):
                    fpath = os.path.join(DATA_FOLDER, fname)
                    fhash = compute_file_hash(fpath)
                    doc_meta = classify_document(fname)
                    c_ids = file_chunks.get(fname, [])

                    manifest[fname] = {
                        "hash": fhash,
                        "chunk_ids": c_ids,
                        "chunk_count": len(c_ids),
                        "kategori": doc_meta["kategori"],
                        "prodi": doc_meta["prodi"],
                        "jenjang": doc_meta["jenjang"]
                    }

        save_manifest(manifest)
        print(f"[Sync] Auto-bootstrap sukses: manifest dibuat untuk {len(manifest)} file!")
    except Exception as e:
        print(f"[Sync] Gagal auto-bootstrap: {e}")
    return manifest


# ═══════════════════════════════════════════════════════════════
#  INCREMENTAL INDEXING
# ═══════════════════════════════════════════════════════════════


def sync_vectordb(force_rebuild=False):
    """
    Sinkronisasi incremental: hanya tambah/update/hapus file yang berubah.
    Bandingkan hash file saat ini dengan manifest terakhir.

    Args:
        force_rebuild: Jika True, hapus seluruh database dan bangun ulang dari awal.

    Returns:
        tuple: (vectordb_instance, stats_dict)
        stats_dict = {"added": int, "updated": int, "deleted": int, "unchanged": int}
    """
    global _vectordb_instance, _bm25_instance, _bm25_corpus, _bm25_metadata

    embeddings = get_embeddings()

    # ── Force Rebuild: Hapus database lama ──
    if force_rebuild and os.path.exists(VECTOR_DB_PATH):
        import shutil, gc
        if _vectordb_instance is not None:
            try:
                _vectordb_instance.delete_collection()
            except Exception:
                pass
            _vectordb_instance = None
        gc.collect()
        for attempt in range(5):
            try:
                shutil.rmtree(VECTOR_DB_PATH)
                break
            except Exception:
                import time
                time.sleep(1)

    # ── Buat / Muat Chroma ──
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    vectordb = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embeddings)

    manifest = load_manifest() if not force_rebuild else {}

    # ── Deteksi upgrade dari sistem lama (ada data Chroma tapi belum ada manifest) ──
    if not manifest and not force_rebuild:
        try:
            existing_count = vectordb._collection.count()
            if existing_count > 0:
                print(f"[Sync] Database lama terdeteksi ({existing_count} chunks). Melakukan auto-bootstrap manifest...")
                manifest = _auto_bootstrap_manifest(vectordb)
        except Exception as e:
            print(f"[Sync] Warning saat cek database lama: {e}")

    # ── Scan file .txt di folder data ──
    current_files = {}
    if os.path.exists(DATA_FOLDER):
        for fname in sorted(os.listdir(DATA_FOLDER)):
            if fname.endswith(".txt"):
                fpath = os.path.join(DATA_FOLDER, fname)
                current_files[fname] = compute_file_hash(fpath)

    # ── Tentukan file yang berubah ──
    files_to_add = []
    files_to_update = []
    files_to_delete = []

    for fname, fhash in current_files.items():
        if fname not in manifest:
            files_to_add.append(fname)
        elif manifest[fname]["hash"] != fhash:
            files_to_update.append(fname)

    for fname in list(manifest.keys()):
        if fname not in current_files:
            files_to_delete.append(fname)

    stats = {
        "added": len(files_to_add),
        "updated": len(files_to_update),
        "deleted": len(files_to_delete),
        "unchanged": len(current_files) - len(files_to_add) - len(files_to_update),
    }

    print(f"\n{'='*60}")
    print(f"[Sync] Baru: {stats['added']} | Berubah: {stats['updated']} | "
          f"Dihapus: {stats['deleted']} | Tetap: {stats['unchanged']}")

    # ── Hapus chunks dari file yang dihapus / berubah ──
    for fname in files_to_delete + files_to_update:
        if fname in manifest:
            ids_to_delete = manifest[fname].get("chunk_ids", [])
            if ids_to_delete:
                try:
                    # Chroma batch delete (500 per batch untuk safety)
                    for i in range(0, len(ids_to_delete), 500):
                        batch = ids_to_delete[i:i+500]
                        vectordb.delete(ids=batch)
                except Exception as e:
                    print(f"  ⚠ Gagal hapus chunks {fname}: {e}")

            if fname in files_to_delete:
                del manifest[fname]
                print(f"  🗑 {fname} dihapus dari index")

    # ── Tambah file baru / yang berubah ──
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for fname in files_to_add + files_to_update:
        fpath = os.path.join(DATA_FOLDER, fname)

        # Coba baca file
        try:
            loader = TextLoader(fpath, encoding="utf-8")
            docs = loader.load()
        except Exception:
            try:
                loader = TextLoader(fpath, encoding="latin-1")
                docs = loader.load()
            except Exception as e:
                print(f"  ✗ Gagal membaca {fname}: {e}")
                continue

        chunks = splitter.split_documents(docs)
        doc_meta = classify_document(fname)

        chunk_ids = []
        texts = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # ID unik & deterministik per chunk: MD5(namafile::index)
            cid = hashlib.md5(f"{fname}::chunk::{i}".encode()).hexdigest()
            chunk_ids.append(cid)
            texts.append(chunk.page_content)
            metadatas.append({
                "source": doc_meta["source"],
                "kategori": doc_meta["kategori"],
                "prodi": doc_meta["prodi"],
                "jenjang": doc_meta["jenjang"],
                "chunk_index": i,
            })

        if texts:
            vectordb.add_texts(texts=texts, metadatas=metadatas, ids=chunk_ids)

        manifest[fname] = {
            "hash": current_files[fname],
            "chunk_ids": chunk_ids,
            "chunk_count": len(chunk_ids),
            "kategori": doc_meta["kategori"],
            "prodi": doc_meta["prodi"],
            "jenjang": doc_meta["jenjang"],
        }

        action = "➕" if fname in files_to_add else "🔄"
        print(f"  {action} {fname} ({len(chunk_ids)} chunks)")

    save_manifest(manifest)
    _vectordb_instance = vectordb

    # Rebuild BM25 index dari seluruh chunks
    _rebuild_bm25_index()

    try:
        total_chunks = vectordb._collection.count()
    except Exception:
        total_chunks = "?"
    print(f"[Sync] Selesai! Total chunks di database: {total_chunks}")
    print(f"{'='*60}\n")

    return vectordb, stats


def _rebuild_bm25_index():
    """Bangun ulang BM25 index dari seluruh chunks di vector database."""
    global _bm25_instance, _bm25_corpus, _bm25_metadata

    if not HAS_BM25:
        _bm25_instance = None
        _bm25_corpus = []
        _bm25_metadata = []
        return

    vectordb = _vectordb_instance
    if vectordb is None:
        _bm25_instance = None
        _bm25_corpus = []
        _bm25_metadata = []
        return

    try:
        all_data = vectordb.get(include=["documents", "metadatas"])
    except Exception:
        _bm25_instance = None
        _bm25_corpus = []
        _bm25_metadata = []
        return

    documents = all_data.get("documents", [])
    metadatas = all_data.get("metadatas", [])

    if not documents:
        _bm25_instance = None
        _bm25_corpus = []
        _bm25_metadata = []
        return

    # Tokenisasi sederhana untuk BM25 (split by whitespace)
    tokenized = [doc.lower().split() for doc in documents]
    _bm25_instance = BM25Okapi(tokenized)
    _bm25_corpus = documents
    _bm25_metadata = metadatas

    print(f"[BM25] Index dibangun: {len(documents)} chunks")


# ═══════════════════════════════════════════════════════════════
#  SINGLETON & LEGACY SUPPORT
# ═══════════════════════════════════════════════════════════════

def get_vectordb_instance():
    """Lazy-load vector database dan BM25 index (pertama kali dipanggil saat ada pertanyaan)."""
    global _vectordb_instance
    if _vectordb_instance is None:
        chroma_db = os.path.join(VECTOR_DB_PATH, "chroma.sqlite3")
        manifest_exists = os.path.exists(MANIFEST_PATH)

        if os.path.exists(chroma_db) and manifest_exists:
            # Database + manifest ada → load langsung (cepat)
            _vectordb_instance = Chroma(
                persist_directory=VECTOR_DB_PATH,
                embedding_function=get_embeddings()
            )
            _rebuild_bm25_index()
        else:
            # Belum ada database atau belum ada manifest → sync dari awal
            sync_vectordb(force_rebuild=True)
    return _vectordb_instance


def build_vectordb():
    """Legacy: membangun database dari awal (backward-compatible)."""
    vdb, _ = sync_vectordb(force_rebuild=True)
    return vdb


def reset_vectordb():
    """Legacy: menghapus dan membangun ulang database (backward-compatible)."""
    vdb, _ = sync_vectordb(force_rebuild=True)
    return vdb


# ═══════════════════════════════════════════════════════════════
#  HYBRID SEARCH: BM25 + DENSE VECTOR + RRF
# ═══════════════════════════════════════════════════════════════

def reciprocal_rank_fusion(rankings, k=60):
    """
    Gabungkan beberapa ranked list menggunakan Reciprocal Rank Fusion.
    Skor RRF = Σ 1/(k + rank) untuk setiap ranking list.
    Paper: Cormack et al. (2009)
    """
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            doc_key = item["content_hash"]
            if doc_key not in scores:
                scores[doc_key] = {
                    "score": 0.0,
                    "content": item["content"],
                    "metadata": item["metadata"],
                }
            scores[doc_key]["score"] += 1.0 / (k + rank + 1)

    return sorted(scores.values(), key=lambda x: x["score"], reverse=True)


def hybrid_search(question, vectordb, k=5):
    """
    Pencarian hybrid: Dense Vector (Chroma) + BM25 Sparse, digabung dengan RRF.
    Jika BM25 belum tersedia, fallback ke dense-only search.
    """
    global _bm25_instance, _bm25_corpus, _bm25_metadata

    rankings = []

    # ── 1. Dense Search (Chroma Semantic Similarity) ──
    try:
        dense_results = vectordb.similarity_search_with_score(question, k=10)
        dense_ranking = []
        for doc, score in dense_results:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            dense_ranking.append({
                "content_hash": content_hash,
                "content": doc.page_content,
                "metadata": doc.metadata,
            })
        if dense_ranking:
            rankings.append(dense_ranking)
    except Exception as e:
        print(f"[Search] Dense search error: {e}")

    # ── 2. BM25 Sparse Search (Keyword Matching) ──
    if HAS_BM25 and _bm25_instance is not None and _bm25_corpus:
        try:
            tokenized_query = question.lower().split()
            bm25_scores = _bm25_instance.get_scores(tokenized_query)

            # Ambil top 10 hasil BM25
            top_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:10]

            bm25_ranking = []
            for idx in top_indices:
                if bm25_scores[idx] > 0:  # Hanya ambil yang relevan
                    content_hash = hashlib.md5(_bm25_corpus[idx].encode()).hexdigest()
                    bm25_ranking.append({
                        "content_hash": content_hash,
                        "content": _bm25_corpus[idx],
                        "metadata": _bm25_metadata[idx] if idx < len(_bm25_metadata) else {},
                    })
            if bm25_ranking:
                rankings.append(bm25_ranking)
        except Exception as e:
            print(f"[Search] BM25 search error: {e}")

    # ── 3. RRF Fusion ──
    if not rankings:
        return []

    if len(rankings) == 1:
        # Hanya satu sumber tersedia → kembalikan langsung
        return [{"content": r["content"], "metadata": r["metadata"]} for r in rankings[0][:k]]

    fused = reciprocal_rank_fusion(rankings)
    return fused[:k]


# ═══════════════════════════════════════════════════════════════
#  GET CONTEXT — Public API (dipanggil oleh app.py)
# ═══════════════════════════════════════════════════════════════

def get_context(question):
    """
    Ambil konteks relevan dari vector database berdasarkan pertanyaan.

    Returns:
        tuple: (context_string, sources_list)
        - context_string: teks gabungan untuk dikirim ke LLM sebagai referensi
        - sources_list: list nama sumber yang sudah di-prettify untuk sitasi
    """
    vectordb = get_vectordb_instance()

    if vectordb is None:
        return "Tidak ada dokumen referensi di database.", []

    # ═══ 1. HYBRID SEARCH (BM25 + Dense + RRF) ═══
    search_results = hybrid_search(question, vectordb, k=5)

    context_chunks = []
    sources = set()

    for result in search_results:
        context_chunks.append(result["content"])
        source_name = result["metadata"].get("source", "")
        if source_name:
            sources.add(source_name)

    # ═══ 2. KEYWORD SEARCH / EXACT MATCH FALLBACK ═══
    # Dipertahankan dari versi skripsi karena sangat akurat untuk kode kelas & nama dosen.
    # Ini adalah "emergency net" jika hybrid search gagal menangkap entitas spesifik.
    keyword = question.lower().strip()
    exact_matches = set()

    # 2a. Deteksi kode kelas spesifik (misal: 1ka01, 2ia02)
    class_codes = re.findall(r'\b[1-4]?[a-z]{2}\d{2}\b', keyword)
    if class_codes:
        for file in os.listdir(DATA_FOLDER):
            if file.endswith(".txt") and "daftar_dosen_kelas" in file.lower():
                filepath = os.path.join(DATA_FOLDER, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            if any(code in line.lower() for code in class_codes):
                                exact_matches.add(f"[Sumber: {file}] {line.strip()}")
                                sources.add(file)
                except Exception:
                    pass

    # 2b. Pencarian Nama Dosen / Mahasiswa (hanya jika query pendek 1-5 kata)
    if len(keyword) > 2 and len(keyword.split()) <= 5:
        for file in os.listdir(DATA_FOLDER):
            if file.endswith(".txt"):
                filepath = os.path.join(DATA_FOLDER, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            if re.search(r'\b' + re.escape(keyword) + r'\b', line.lower()):
                                if file.startswith("daftar_dosen_kelas"):
                                    prefix = "[Daftar Dosen Wali Kelas]"
                                elif file == "daftar_dosen_pi.txt":
                                    prefix = "[Daftar Dosen Pembimbing PI]"
                                elif file == "daftar_koordinator_matkul.txt":
                                    prefix = "[Daftar Dosen Pengajar Mata Kuliah]"
                                else:
                                    prefix = f"[Sumber: {file}]"
                                exact_matches.add(f"{prefix} {line.strip()}")
                                sources.add(file)
                except Exception:
                    pass

    if exact_matches:
        # Gabungkan maks 60 baris temuan agar tidak overflow context window
        exact_text = "\n".join(list(exact_matches)[:60])
        context_chunks.insert(0, exact_text)

    context = "\n\n".join(context_chunks)

    # Prettify source names untuk ditampilkan ke user
    pretty_sources = sorted(set(prettify_source(s) for s in sources))

    return context, pretty_sources