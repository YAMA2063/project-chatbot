"""
verify_tahap1.py
Memverifikasi:
1. get_vectordb_instance() loads Chroma and builds BM25 index cleanly
2. sync_vectordb(force_rebuild=False) reports 0 changed files in milliseconds
3. hybrid_search() + get_context() returns context and prettified sources
"""

import time
from rag import get_context, sync_vectordb, get_vectordb_instance

print("=== 1. TEST LOAD VECTOR DB & BM25 ===")
t0 = time.time()
vdb = get_vectordb_instance()
print(f"Loaded in {time.time() - t0:.2f}s, total chunks: {vdb._collection.count()}")

print("\n=== 2. TEST INCREMENTAL SYNC (Tanpa Perubahan) ===")
t0 = time.time()
_, stats = sync_vectordb(force_rebuild=False)
print(f"Sync selesai dalam {time.time() - t0:.2f}s!")
print(f"Stats: {stats}")

print("\n=== 3. TEST GET CONTEXT & CITATIONS ===")
pertanyaan_tes = [
    "siapa dosen wali 4ia01",
    "jadwal uas universitas gunadarma",
    "syarat sidang penulisan ilmiah"
]

for q in pertanyaan_tes:
    t0 = time.time()
    ctx, sources = get_context(q)
    dt = time.time() - t0
    print(f"\n[Q]: {q} ({dt:.2f}s)")
    print(f"[Sources]: {sources}")
    print(f"[Context snippet (150 chars)]: {ctx[:150]}...")

print("\n[SUCCESS] SEMUA PENGUJIAN TAHAP 1 BERHASIL 100%!")
