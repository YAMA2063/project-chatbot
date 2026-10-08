"""
bootstrap_manifest.py
Membangun manifest dari 3.539 chunk yang SUDAH ADA di Chroma tanpa perlu re-embedding (hemat 50 menit!).
Juga memperkaya metadata setiap chunk dengan kategori, prodi, dan jenjang.
"""

import os
import hashlib
import json
from collections import defaultdict
from rag import classify_document, compute_file_hash, save_manifest, MANIFEST_PATH, DATA_FOLDER, VECTOR_DB_PATH
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def bootstrap():
    print("[Bootstrap] Menghubungkan ke Chroma...")
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")
    vectordb = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embeddings)

    count = vectordb._collection.count()
    print(f"[Bootstrap] Ditemukan {count} chunks di Chroma.")

    if count == 0:
        print("[Bootstrap] Chroma kosong, tidak perlu migrasi.")
        return

    print("[Bootstrap] Mengambil metadata seluruh chunk...")
    all_data = vectordb.get(include=["metadatas"])
    ids = all_data.get("ids", [])
    metas = all_data.get("metadatas", [])

    # Petakan file -> list chunk IDs
    file_chunks = defaultdict(list)
    update_ids = []
    update_metas = []

    for cid, meta in zip(ids, metas):
        raw_src = meta.get("source", "")
        # Ambil nama file saja (hilangkan path ./data preprocessing/ dsb)
        fname = os.path.basename(raw_src.replace("\\", "/"))
        file_chunks[fname].append(cid)

        # Tambahkan metadata baru jika belum ada
        doc_meta = classify_document(fname)
        new_meta = {
            "source": fname,
            "kategori": doc_meta["kategori"],
            "prodi": doc_meta["prodi"],
            "jenjang": doc_meta["jenjang"]
        }
        update_ids.append(cid)
        update_metas.append(new_meta)

    print(f"[Bootstrap] Berhasil memetakan {len(file_chunks)} file unik dari {len(ids)} chunks.")

    # Update metadata di Chroma secara batch (500 per batch)
    print("[Bootstrap] Memperbarui metadata (kategori, prodi, jenjang) di Chroma...")
    batch_size = 500
    for i in range(0, len(update_ids), batch_size):
        b_ids = update_ids[i:i+batch_size]
        b_metas = update_metas[i:i+batch_size]
        try:
            vectordb._collection.update(ids=b_ids, metadatas=b_metas)
        except Exception as e:
            print(f"  [Warning batch {i}] {e}")

    # Buat manifest berbasis file di DATA_FOLDER
    manifest = {}
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
    print(f"[Bootstrap] SELESAI! Manifest tersimpan di {MANIFEST_PATH} dengan {len(manifest)} file.")

if __name__ == "__main__":
    bootstrap()
