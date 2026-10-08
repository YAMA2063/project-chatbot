"""
ablation_study.py - Tahap 2: Ablation Study & Retrieval Evaluation
===================================================================
Evaluasi Retrieval Komparatif 4 Skenario:
  1. Raw Query + Dense
  2. Transformed Query + Dense
  3. Raw Query + Hybrid
  4. Transformed Query + Hybrid

Metrik yang dihitung:
- Hit Rate @ K (apakah dokumen ground-truth muncul di top-K retrieval?)
- Mean Reciprocal Rank (MRR)
- Context Precision (berapa % retrieved chunks yang berasal dari sumber benar?)
- Rata-rata Latensi Retrieval (detik)

Output: hasil JSON + tabel console + grafik PNG (via visualisasi_ablation.py)
"""

import os
import sys
import re
import json
import time
import hashlib

# Pastikan encoding stdout UTF-8 di Windows
sys.stdout.reconfigure(encoding="utf-8")

# ── Import dari project ──
from rag import (
    get_vectordb_instance, hybrid_search, reciprocal_rank_fusion,
    _bm25_instance, _bm25_corpus, _bm25_metadata,
    HAS_BM25, DATA_FOLDER, prettify_source
)

# ═══════════════════════════════════════════════════════════════
#  TEST SET BERSTRATA — 30 skenario uji
#  Setiap skenario punya:
#    - raw_query: pertanyaan asli mahasiswa (bahasa kasual/gaul)
#    - transformed_query: query setelah melalui perbaiki_pertanyaan()
#    - ground_truth_sources: list nama file .txt yang SEHARUSNYA muncul
#    - domain: kategori layanan (jadwal, dosen, administrasi, dll.)
#    - intent: jenis intent (factoid, navigasi, prosedural)
# ═══════════════════════════════════════════════════════════════

TEST_SET = [
    # ── DOMAIN: DOSEN WALI (Factoid, Kode Kelas) ──
    {
        "id": 1, "domain": "dosen_wali", "intent": "factoid",
        "raw_query": "siapa wali kelas 1ka01",
        "transformed_query": "Dosen Wali Kelas 1KA01",
        "ground_truth_sources": ["daftar_dosen_kelas1.txt"],
    },
    {
        "id": 2, "domain": "dosen_wali", "intent": "factoid",
        "raw_query": "wali 4ia01 sapa sih",
        "transformed_query": "Dosen Wali Kelas 4IA01",
        "ground_truth_sources": ["daftar_dosen_kelas4.txt"],
    },
    {
        "id": 3, "domain": "dosen_wali", "intent": "factoid",
        "raw_query": "wali kelas 2ka28",
        "transformed_query": "Dosen Wali Kelas 2KA28",
        "ground_truth_sources": ["daftar_dosen_kelas2.txt"],
    },
    {
        "id": 4, "domain": "dosen_wali", "intent": "factoid",
        "raw_query": "wali kelas 3ia05 dong",
        "transformed_query": "Dosen Wali Kelas 3IA05",
        "ground_truth_sources": ["daftar_dosen_kelas3.txt"],
    },
    # ── DOMAIN: DOSEN PENGAJAR (Factoid, Nama Dosen) ──
    {
        "id": 5, "domain": "dosen_pengajar", "intent": "factoid",
        "raw_query": "bu lulu ngajar apa",
        "transformed_query": "Lulu",
        "ground_truth_sources": ["daftar_koordinator_matkul.txt", "daftar_dosen_kelas4.txt",
                                  "daftar_dosen_kelas3.txt", "daftar_dosen_kelas2.txt",
                                  "daftar_dosen_kelas1.txt"],
    },
    {
        "id": 6, "domain": "dosen_pengajar", "intent": "factoid",
        "raw_query": "siapa yang ngajar basis data",
        "transformed_query": "Koordinator Mata Kuliah Basis Data",
        "ground_truth_sources": ["daftar_koordinator_matkul.txt"],
    },
    # ── DOMAIN: DOSEN PI (Factoid) ──
    {
        "id": 7, "domain": "dosen_pi", "intent": "factoid",
        "raw_query": "dosen pembimbing pi kelas 4ka27",
        "transformed_query": "Dosen Pembimbing PI 4KA27",
        "ground_truth_sources": ["daftar_dosen_pi.txt"],
    },
    {
        "id": 8, "domain": "dosen_pi", "intent": "factoid",
        "raw_query": "pi 4ia12 dibimbing siapa",
        "transformed_query": "Dosen Pembimbing PI 4IA12",
        "ground_truth_sources": ["daftar_dosen_pi.txt"],
    },
    # ── DOMAIN: MATA KULIAH (Factoid, Per Jurusan) ──
    {
        "id": 9, "domain": "mata_kuliah", "intent": "factoid",
        "raw_query": "matkul semester 3 sistem informasi",
        "transformed_query": "Mata Kuliah S1 Sistem Informasi",
        "ground_truth_sources": ["daftar mata kuliah s1 sistem informasi.txt"],
    },
    {
        "id": 10, "domain": "mata_kuliah", "intent": "factoid",
        "raw_query": "jurusan informatika belajar apa aja",
        "transformed_query": "Mata Kuliah S1 Informatika",
        "ground_truth_sources": ["daftar mata kuliah s1 informatika.txt"],
    },
    {
        "id": 11, "domain": "mata_kuliah", "intent": "factoid",
        "raw_query": "matkul akuntansi d3",
        "transformed_query": "Mata Kuliah D3 Akuntansi Komputer",
        "ground_truth_sources": ["daftar mata kuliah d3 akuntansi komputer.txt"],
    },
    {
        "id": 12, "domain": "mata_kuliah", "intent": "factoid",
        "raw_query": "daftar matkul teknik sipil",
        "transformed_query": "Mata Kuliah S1 Teknik Sipil",
        "ground_truth_sources": ["daftar mata kuliah s1 teknik sipil.txt"],
    },
    # ── DOMAIN: JADWAL (Factoid / Navigasi) ──
    {
        "id": 13, "domain": "jadwal", "intent": "navigasi",
        "raw_query": "jadwal uas kapan ya",
        "transformed_query": "Jadwal UAS",
        "ground_truth_sources": ["dataset_jadwal_ujian_utama.txt"],
    },
    {
        "id": 14, "domain": "jadwal", "intent": "navigasi",
        "raw_query": "gimana cara liat jadwal kuliah",
        "transformed_query": "Jadwal Kuliah",
        "ground_truth_sources": ["panduan_jadwal_kuliah.txt"],
    },
    # ── DOMAIN: ADMINISTRASI (Prosedural) ──
    {
        "id": 15, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara isi krs gimana",
        "transformed_query": "Panduan KRS",
        "ground_truth_sources": ["krs.txt"],
    },
    {
        "id": 16, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara daftar wisuda",
        "transformed_query": "Prosedur Wisuda",
        "ground_truth_sources": ["prosedur wisuda.txt"],
    },
    {
        "id": 17, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "syarat sidang skripsi apa aja",
        "transformed_query": "Syarat Sidang Skripsi",
        "ground_truth_sources": ["akademik.txt", "daftar sidang.txt"],
    },
    {
        "id": 18, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara aktivasi mahasiswa baru",
        "transformed_query": "Aktivasi Mahasiswa",
        "ground_truth_sources": ["aktivasi.txt"],
    },
    {
        "id": 19, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara urus surat keterangan",
        "transformed_query": "Surat Keterangan",
        "ground_truth_sources": ["surat keterangan.txt"],
    },
    {
        "id": 20, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara bikin blanko pembayaran",
        "transformed_query": "Blanko Pembayaran",
        "ground_truth_sources": ["blanko pembayaran.txt"],
    },
    # ── DOMAIN: PROFIL KAMPUS (Factoid) ──
    {
        "id": 21, "domain": "profil", "intent": "factoid",
        "raw_query": "visi misi gunadarma apa",
        "transformed_query": "Visi Misi Universitas Gunadarma",
        "ground_truth_sources": ["profil_universitas_gunadarma.txt"],
    },
    {
        "id": 22, "domain": "profil", "intent": "factoid",
        "raw_query": "akreditasi sistem informasi berapa",
        "transformed_query": "Akreditasi Sistem Informasi",
        "ground_truth_sources": ["profil_sistem_informasi_akreditasi.txt"],
    },
    {
        "id": 23, "domain": "profil", "intent": "factoid",
        "raw_query": "visi misi jurusan informatika",
        "transformed_query": "Visi Misi Informatika",
        "ground_truth_sources": ["profil_informatika_visi_misi.txt"],
    },
    # ── DOMAIN: PEDOMAN (Prosedural) ──
    {
        "id": 24, "domain": "pedoman", "intent": "prosedural",
        "raw_query": "aturan tata krama mahasiswa apa aja",
        "transformed_query": "Tata Krama Mahasiswa",
        "ground_truth_sources": ["BUKU PEDOMAN TATA KRAMA MAHASISWA.txt"],
    },
    {
        "id": 25, "domain": "pedoman", "intent": "prosedural",
        "raw_query": "aturan penasehat akademik",
        "transformed_query": "Penasehat Akademik PA Wali Kelas",
        "ground_truth_sources": ["BUKU PEDOMAN PENASEHAT AKADEMIK PA & WALI KELAS.txt"],
    },
    # ── DOMAIN: BERITA (Factoid) ──
    {
        "id": 26, "domain": "berita", "intent": "factoid",
        "raw_query": "berita terbaru baak apa",
        "transformed_query": "Berita Terbaru BAAK",
        "ground_truth_sources": ["berita_terbaru_baak.txt"],
    },
    # ── DOMAIN: RPS (Factoid) ──
    {
        "id": 27, "domain": "rps", "intent": "factoid",
        "raw_query": "info rps gimana",
        "transformed_query": "Informasi RPS",
        "ground_truth_sources": ["informasi_rps.txt", "informasi_kontak_rps.txt"],
    },
    # ── DOMAIN: SKPI (Prosedural) ──
    {
        "id": 28, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "cara ngurus skpi",
        "transformed_query": "SKPI",
        "ground_truth_sources": ["skpi.txt"],
    },
    # ── DOMAIN: KALENDER AKADEMIK (Factoid) ──
    {
        "id": 29, "domain": "jadwal", "intent": "factoid",
        "raw_query": "kalender akademik gunadarma",
        "transformed_query": "Kalender Akademik",
        "ground_truth_sources": ["kalender_akademik.txt"],
    },
    # ── DOMAIN: UJIAN BENTROK (Prosedural) ──
    {
        "id": 30, "domain": "administrasi", "intent": "prosedural",
        "raw_query": "ujian bentrok gimana solusinya",
        "transformed_query": "Pengurusan Ujian Bentrok",
        "ground_truth_sources": ["pengurusan_ujian_bentrok.txt"],
    },
]


# ═══════════════════════════════════════════════════════════════
#  FUNGSI RETRIEVAL PER SKENARIO
# ═══════════════════════════════════════════════════════════════

def dense_only_search(question, vectordb, k=5):
    """Pencarian hanya menggunakan Dense Vector (Chroma similarity_search)."""
    try:
        results = vectordb.similarity_search_with_score(question, k=k)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc, _ in results]
    except Exception:
        return []


def run_retrieval(query, vectordb, mode="hybrid", k=5):
    """
    Menjalankan retrieval dengan mode tertentu.
    mode: "dense" | "hybrid"
    """
    if mode == "dense":
        return dense_only_search(query, vectordb, k=k)
    else:
        return hybrid_search(query, vectordb, k=k)


# ═══════════════════════════════════════════════════════════════
#  METRIK EVALUASI
# ═══════════════════════════════════════════════════════════════

def compute_hit_rate(retrieved_sources, ground_truth_sources):
    """Hit Rate@K: apakah minimal 1 ground-truth source muncul di retrieved sources?"""
    for gt in ground_truth_sources:
        gt_lower = gt.lower()
        for rs in retrieved_sources:
            if gt_lower in rs.lower() or rs.lower() in gt_lower:
                return 1.0
    return 0.0


def compute_reciprocal_rank(retrieved_sources, ground_truth_sources):
    """MRR: 1/rank dari ground-truth pertama yang ditemukan."""
    for rank, rs in enumerate(retrieved_sources, 1):
        rs_lower = rs.lower()
        for gt in ground_truth_sources:
            if gt.lower() in rs_lower or rs_lower in gt.lower():
                return 1.0 / rank
    return 0.0


def compute_context_precision(retrieved_sources, ground_truth_sources):
    """Context Precision: berapa % retrieved chunks yang berasal dari sumber benar?"""
    if not retrieved_sources:
        return 0.0
    hits = 0
    for rs in retrieved_sources:
        rs_lower = rs.lower()
        for gt in ground_truth_sources:
            if gt.lower() in rs_lower or rs_lower in gt.lower():
                hits += 1
                break
    return hits / len(retrieved_sources)


# ═══════════════════════════════════════════════════════════════
#  MAIN: RUN ABLATION STUDY
# ═══════════════════════════════════════════════════════════════

SCENARIOS = [
    {"name": "Raw + Dense",         "query_key": "raw_query",         "mode": "dense"},
    {"name": "Transformed + Dense", "query_key": "transformed_query", "mode": "dense"},
    {"name": "Raw + Hybrid",        "query_key": "raw_query",         "mode": "hybrid"},
    {"name": "Transformed + Hybrid","query_key": "transformed_query", "mode": "hybrid"},
]


def run_ablation():
    print("=" * 70)
    print("  ABLATION STUDY - 4 Skenario Retrieval x 30 Pertanyaan Uji")
    print("  Evaluasi Kuantitatif Performa Information Retrieval")
    print("=" * 70)

    # Load vectordb & BM25
    print("\n[1/3] Memuat vector database dan BM25 index...")
    vectordb = get_vectordb_instance()
    total_chunks = vectordb._collection.count()
    print(f"      Database siap: {total_chunks} chunks, BM25 = {HAS_BM25}")

    K = 5  # Top-K retrieval

    all_results = {}

    for scenario in SCENARIOS:
        sname = scenario["name"]
        print(f"\n[2/3] Menjalankan skenario: {sname}...")

        hit_rates = []
        mrrs = []
        precisions = []
        latencies = []
        per_query_results = []

        for test in TEST_SET:
            query = test[scenario["query_key"]]
            gt_sources = test["ground_truth_sources"]

            t0 = time.time()
            results = run_retrieval(query, vectordb, mode=scenario["mode"], k=K)
            latency = time.time() - t0

            # Ekstrak source names dari hasil retrieval
            retrieved_sources = []
            for r in results:
                src = r.get("metadata", {}).get("source", "")
                if src:
                    # Ambil basename saja
                    src = os.path.basename(src.replace("\\", "/"))
                    retrieved_sources.append(src)

            hr = compute_hit_rate(retrieved_sources, gt_sources)
            rr = compute_reciprocal_rank(retrieved_sources, gt_sources)
            cp = compute_context_precision(retrieved_sources, gt_sources)

            hit_rates.append(hr)
            mrrs.append(rr)
            precisions.append(cp)
            latencies.append(latency)

            per_query_results.append({
                "id": test["id"],
                "domain": test["domain"],
                "query": query,
                "ground_truth": gt_sources,
                "retrieved": retrieved_sources[:K],
                "hit": hr,
                "rr": rr,
                "precision": cp,
                "latency_s": round(latency, 3),
            })

        avg_hr = sum(hit_rates) / len(hit_rates) * 100
        avg_mrr = sum(mrrs) / len(mrrs)
        avg_cp = sum(precisions) / len(precisions) * 100
        avg_lat = sum(latencies) / len(latencies)

        all_results[sname] = {
            "hit_rate_pct": round(avg_hr, 2),
            "mrr": round(avg_mrr, 4),
            "context_precision_pct": round(avg_cp, 2),
            "avg_latency_s": round(avg_lat, 3),
            "per_query": per_query_results,
        }

        print(f"      Hit Rate@{K}: {avg_hr:.1f}%  |  MRR: {avg_mrr:.3f}  |  "
              f"Context Precision: {avg_cp:.1f}%  |  Avg Latency: {avg_lat:.3f}s")

    # ── Simpan hasil ke JSON ──
    output_path = os.path.join(os.path.dirname(__file__), "ablation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n[3/3] Hasil disimpan ke: {output_path}")

    # ── Cetak tabel ringkasan ──
    print("\n" + "=" * 70)
    print(f"{'Skenario':<28} {'Hit Rate@5':>11} {'MRR':>8} {'Ctx Precision':>14} {'Latency':>10}")
    print("-" * 70)
    for sname, data in all_results.items():
        print(f"{sname:<28} {data['hit_rate_pct']:>10.1f}% {data['mrr']:>7.3f} "
              f"{data['context_precision_pct']:>13.1f}% {data['avg_latency_s']:>9.3f}s")
    print("=" * 70)

    # ── Identifikasi skenario terbaik ──
    best = max(all_results.items(), key=lambda x: (x[1]["hit_rate_pct"], x[1]["mrr"]))
    print(f"\n>>> SKENARIO TERBAIK: {best[0]}")
    print(f"    Hit Rate: {best[1]['hit_rate_pct']}%  |  MRR: {best[1]['mrr']}  |  "
          f"Context Precision: {best[1]['context_precision_pct']}%")

    return all_results


if __name__ == "__main__":
    run_ablation()
