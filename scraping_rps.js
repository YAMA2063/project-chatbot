// === MASTER SCRIPT: AUTO-SCRAPER RPS GUNADARMA ===
// Berfungsi untuk tipe website AJAX (tanpa reload) maupun Hard Reload.

(function() {
    console.log("🚀 [RPS Scraper] Memulai proses...");

    // Inisialisasi Storage jika belum ada
    if (!localStorage.getItem('rps_scraping_active')) {
        console.log("📥 [RPS Scraper] Memulai scraping dari Halaman 1!");
        localStorage.setItem('rps_scraping_active', 'true');
        localStorage.setItem('rps_data', JSON.stringify([]));
        localStorage.setItem('rps_page', '1');
    }

    function scrapeCurrentPage() {
        // Ambil data yang sudah tersimpan
        let scrapedData = JSON.parse(localStorage.getItem('rps_data') || "[]");
        let currentPage = parseInt(localStorage.getItem('rps_page') || "1");

        console.log(`📄 [RPS Scraper] Sedang menyedot Halaman ${currentPage}...`);

        // 1. SEDOT TABEL DI HALAMAN INI
        const tableRows = document.querySelectorAll('table tbody tr');
        
        if (tableRows.length === 0) {
            console.error("❌ [RPS Scraper] Tabel tidak ditemukan! Pastikan Anda berada di halaman pencarian RPS.");
            return;
        }

        tableRows.forEach(row => {
            const columns = row.querySelectorAll('td');
            if (columns.length >= 5) {
                const fakultas = columns[1].innerText.trim();
                const prodi = columns[2].innerText.trim();
                const kode = columns[3].innerText.trim();
                const matkul = columns[4].innerText.trim();
                
                // Ambil URL file dari kolom ke-6
                const fileElement = columns[5].querySelector('a');
                const fileUrl = fileElement ? fileElement.href : 'Tidak ada file';
                
                // Skip header row
                if (fakultas.toLowerCase() === 'fakultas' || fakultas.toLowerCase() === '') return;
                
                const barisData = `RPS | Fakultas: ${fakultas}, Jurusan: ${prodi}, Kode: ${kode}, Matkul: ${matkul}, URL: ${fileUrl}`;
                // Hindari duplikat di halaman yang sama
                if (!scrapedData.includes(barisData)) {
                    scrapedData.push(barisData);
                }
            }
        });

        localStorage.setItem('rps_data', JSON.stringify(scrapedData));

        // 2. CARI TOMBOL "NEXT" (Cari angka halaman berikutnya)
        const targetPageNumber = (currentPage + 1).toString();
        const allLinks = Array.from(document.querySelectorAll('a'));
        
        // Cari link <a> yang tulisannya persis angka halaman selanjutnya (misal: "2")
        const nextButton = allLinks.find(a => a.textContent.trim() === targetPageNumber);

        // Jika tombol halaman selanjutnya ADA
        if (nextButton) {
            console.log(`⏭️ [RPS Scraper] Pindah ke Halaman ${currentPage + 1}...`);
            localStorage.setItem('rps_page', (currentPage + 1).toString());
            
            nextButton.click();
            
            // Coba eksekusi lagi setelah 3 detik (berfungsi jika web pakai AJAX tanpa reload)
            // Jika web melakukan hard reload, baris ini otomatis mati dan Anda harus paste ulang scriptnya.
            setTimeout(scrapeCurrentPage, 3000);
            
        } else {
            console.log("✅ [RPS Scraper] SELESAI! Mencapai halaman terakhir.");
            console.log(`🎉 Total data berhasil disedot: ${scrapedData.length} Mata Kuliah!`);
            
            const blob = new Blob([scrapedData.join('\n')], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'daftar_rps_master.txt';
            a.click();

            localStorage.removeItem('rps_scraping_active');
            localStorage.removeItem('rps_data');
            localStorage.removeItem('rps_page');
        }
    }

    // Jalankan fungsi
    scrapeCurrentPage();
})();
