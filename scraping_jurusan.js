// === MASTER SCRIPT: MENU JURUSAN SCRAPER ===
// Ekstensi untuk menyedot menu navigasi website jurusan agar tidak tertukar!

(function() {
    console.log("🚀 [Menu Scraper] Memulai proses penyedotan link penting...");

    // 1. Ambil nama jurusan dari URL website saat ini (misal: informatika.gunadarma.ac.id -> INFORMATIKA)
    const hostname = window.location.hostname;
    let namaJurusan = hostname.split('.')[0].toUpperCase();
    
    // Jika url-nya www, ambil kata keduanya
    if (namaJurusan === 'WWW') {
        namaJurusan = hostname.split('.')[1].toUpperCase();
    }
    
    console.log(`📌 Mendeteksi website Jurusan: ${namaJurusan}`);

    // 2. Cari semua link di area Header/Navigasi
    // Kita cari tag <a> yang ada di dalam elemen nav, header, atau class yang mengandung kata menu
    const navLinks = document.querySelectorAll('nav a, header a, .menu a, .navbar a');
    
    let scrapedData = [];
    let uniqueUrls = new Set();

    navLinks.forEach(link => {
        const menuText = link.innerText.trim();
        const url = link.href;

        // Validasi: Pastikan teks menu tidak kosong dan bukan link palsu (#)
        if (menuText && url && !url.endsWith('#') && !uniqueUrls.has(url)) {
            uniqueUrls.add(url);
            
            // Format super rapi & anti-bentrok untuk AI
            const barisData = `Menu Website Jurusan ${namaJurusan} | Nama Menu: ${menuText} | URL: ${url}`;
            scrapedData.push(barisData);
        }
    });

    if (scrapedData.length === 0) {
        console.warn("⚠️ [Menu Scraper] Tidak menemukan menu. Mencoba mengambil semua link penting di halaman...");
        // Fallback: Ambil semua link yang teksnya lumayan panjang (bukan sekadar icon)
        document.querySelectorAll('a').forEach(link => {
            const menuText = link.innerText.trim();
            const url = link.href;
            if (menuText.length > 3 && url && !url.endsWith('#') && url.includes(hostname) && !uniqueUrls.has(url)) {
                uniqueUrls.add(url);
                scrapedData.push(`Menu Website Jurusan ${namaJurusan} | Nama Menu: ${menuText} | URL: ${url}`);
            }
        });
    }

    console.log(`✅ [Menu Scraper] Berhasil mengekstrak ${scrapedData.length} menu penting!`);

    // 3. Simpan dan Download otomatis
    if (scrapedData.length > 0) {
        const finalContent = `=== KUMPULAN MENU WEBSITE ${namaJurusan} ===\n\n` + scrapedData.join('\n');
        const blob = new Blob([finalContent], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `menu_jurusan_${namaJurusan.toLowerCase()}.txt`;
        a.click();
        console.log(`💾 [Menu Scraper] File 'menu_jurusan_${namaJurusan.toLowerCase()}.txt' sedang diunduh!`);
    } else {
        console.error("❌ Gagal menyedot menu. Website ini mungkin menggunakan struktur menu yang sangat aneh.");
    }
})();
