import pdfplumber
import os
import re

def clean_noise(text):
    if not text: 
        return ""
    # Hapus nomor halaman yang cuma berdiri sendiri di baris baru
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Hapus baris kosong yang berlebihan (maksimal 2 baris kosong berurutan)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_pdf(pdf_path, output_path):
    print(f"Memproses: {os.path.basename(pdf_path)}...")
    all_content = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_content = f"--- Halaman {page_num + 1} ---\n\n"
            
            # 1. Ekstraksi Tabel (Ubah ke Format Markdown)
            tables = page.extract_tables()
            if tables:
                page_content += "[EKSTRAKSI TABEL DETEKSI]\n"
                for table in tables:
                    for row_idx, row in enumerate(table):
                        # Bersihkan sel (jika None atau ada newline (enter) di dalam sel)
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        row_md = "| " + " | ".join(clean_row) + " |"
                        page_content += row_md + "\n"
                        # Tambahkan garis pemisah header setelah baris pertama
                        if row_idx == 0:
                            page_content += "|" + "|".join(["---"] * len(clean_row)) + "|\n"
                    page_content += "\n"
            
            # 2. Ekstraksi Teks (Layout Mode)
            # layout=True mempertahankan spasi spasial asli, mencegah kolom teks menyatu
            text = page.extract_text(layout=True)
            if text:
                page_content += "[EKSTRAKSI TEKS]\n"
                page_content += text + "\n"
                
            all_content.append(clean_noise(page_content))
            
    final_text = "\n\n".join(all_content)
    
    # Simpan ke .txt
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    print(f" Selesai disimpan di: {output_path}")

def main():
    input_dir = "arsip pdf mentah"
    output_dir = "data preprocessing coba"
    
    # Buat folder output jika belum ada
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Ambil semua file PDF
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print("Tidak ada file PDF di folder arsip pdf mentah.")
        return
        
    # UNTUK TESTING: Kita hanya jalankan untuk 2 file pertama yang mungkin punya banyak tabel
    # Anda bisa menghapus [:2] nanti jika ingin memproses seluruh file
    test_files = [f for f in pdf_files if "S1 - SISTEM INFORMASI" in f or "BUKU PEDOMAN PA" in f]
    if not test_files:
        test_files = pdf_files[:2] # Fallback ambil 2 acak
        
    print(f"Memulai ujicoba pada {len(test_files)} file PDF...\n")
    
    for file_name in test_files:
        pdf_path = os.path.join(input_dir, file_name)
        txt_name = file_name.replace(".pdf", ".txt")
        output_path = os.path.join(output_dir, txt_name)
        
        process_pdf(pdf_path, output_path)
        
    print("\nUjicoba selesai! Silakan cek folder 'data preprocessing coba'.")

if __name__ == "__main__":
    main()
