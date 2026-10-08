// === MASTER SCRIPT: KONTEN PROFIL SCRAPER ===
// Ekstensi cerdas untuk menyedot teks bersih dari halaman artikel/profil jurusan

(function() {
    console.log("🚀 [Profil Scraper] Memulai penyedotan teks artikel...");

    // 1. Deteksi Nama Jurusan
    const hostname = window.location.hostname;
    let namaJurusan = hostname.split('.')[0].toUpperCase();
    
    // Jika domainnya umum seperti WWW atau Fakultas (FTI), ambil dari URL path-nya
    if (namaJurusan === 'WWW' || namaJurusan === 'FTI') {
        const pathSegments = window.location.pathname.split('/').filter(p => p.length > 0);
        if (pathSegments.length > 0 && !pathSegments[0].includes('.php')) {
            namaJurusan = pathSegments[0].toUpperCase(); // misal: fti.gunadarma.ac.id/informatika
        } else if (namaJurusan === 'WWW') {
            namaJurusan = hostname.split('.')[1].toUpperCase();
        }
    }

    // 2. Ekstrak Teks Utama (Mencari elemen pembungkus konten)
    let contentArea = document.querySelector('article, main, .entry-content, .post-content, #content, .content');
    if (!contentArea) contentArea = document.body; // Fallback jika struktur webnya aneh

    // 3. Deteksi Judul Halaman (Visi Misi, Keunggulan, dsb) dari DALAM konten
    let judulHalaman = "";
    // Cari judul di dalam area konten untuk menghindari banner header (seperti ucapan Idul Fitri)
    const titleElement = contentArea.querySelector('h1, h2, .entry-title, .page-title');
    if (titleElement && titleElement.textContent.trim().length > 0) {
        judulHalaman = titleElement.textContent.replace(/\s+/g, ' ').trim();
    }
    
    // Fallback ke document.title
    if (!judulHalaman) {
        judulHalaman = document.title.split('-')[0].trim();
    }
    
    // Filter hardcore: Jika judulnya mengandung ucapan/emoji, paksa ganti!
    if (judulHalaman.toLowerCase().includes('selamat') || judulHalaman.includes('✨') || judulHalaman.includes('🌙')) {
        judulHalaman = "Profil " + namaJurusan;
    }

    let extractedText = [];
    
    // Ambil elemen paragraf, daftar, subjudul, class khusus, serta div/span murni
    const elements = contentArea.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, .sub-title, .section-title, div, span');
    
    // Set untuk menghindari duplikasi teks dari elemen bersarang
    const processedTexts = new Set();

    elements.forEach(el => {
        // Hindari mengambil teks yang bocor dari menu navigasi atau footer
        if (el.closest('nav') || el.closest('header') || el.closest('footer') || el.closest('.sidebar') || el.closest('.widget')) return;
        
        let text = el.innerText.trim();
        // Hanya ambil teks yang tidak kosong
        if (text.length > 2 && !processedTexts.has(text)) {
            // Jika elemen adalah div atau span, pastikan dia tidak membungkus elemen lain yang sudah/akan kita proses
            if (el.tagName.toLowerCase() === 'div' || el.tagName.toLowerCase() === 'span') {
                if (el.querySelector('p, li, h1, h2, h3, h4, h5, h6')) return;
            }

            processedTexts.add(text);
            // Beri tanda bullet untuk elemen list agar rapi
            if (el.tagName.toLowerCase() === 'li') {
                text = `- ${text}`;
            } 
            // Beri tanda header untuk subjudul (termasuk h1-h6 dan class spesifik)
            else if (el.tagName.toLowerCase().match(/^h[1-6]$/) || el.classList.contains('sub-title') || el.classList.contains('section-title')) {
                text = `\n## ${text}\n`;
            }

            extractedText.push(text);
        }
    });

    if (extractedText.length === 0) {
        console.error("❌ Gagal menemukan paragraf teks. Pastikan Anda berada di halaman artikel (seperti Visi Misi).");
        return;
    }

    // 4. Format & Download
    const finalContent = `=== JURUSAN ${namaJurusan} ===\nTopik: ${judulHalaman}\nURL Asli: ${window.location.href}\n\nKONTEN:\n` + extractedText.join('\n\n');
    
    const blob = new Blob([finalContent], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    
    // Bersihkan nama file dari karakter spasi/simbol
    let safeTitle = judulHalaman.toLowerCase().replace(/[^a-z0-9]/g, '_').substring(0, 30);
    a.download = `profil_${namaJurusan.toLowerCase()}_${safeTitle}.txt`;
    a.click();
    
    console.log(`✅ [Profil Scraper] Sukses menyedot ${extractedText.length} blok teks! File 'profil_${namaJurusan.toLowerCase()}_${safeTitle}.txt' sedang diunduh.`);
})();
