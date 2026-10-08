// === ALGORITMA EKSTRAKSI DATA (WEB SCRAPING) VIA ASYNCHRONOUS DOM PARSING ===
// Deskripsi: Skrip untuk mengekstrak ribuan baris data tabel Dosen PI yang terpaginasi
// Teknik: HTTP Fetch, Virtual DOM Parsing, Set() Deduplication, dan Politeness Delay.

async function ekstraksiDataTerpaginasi() {
    // 1. Inisialisasi: Mengambil total data dari elemen HTML (Indeks ke-2 untuk Tabel PI)
    const elemenTotal = document.querySelectorAll('p b');
    const totalRecord = elemenTotal.length > 2 ? parseInt(elemenTotal[2].innerText.trim()) : 0;
    
    // Menghitung jumlah halaman (Kapasitas 20 baris per halaman) menggunakan pembulatan ke atas
    const totalHalaman = Math.ceil(totalRecord / 20); 
    
    console.log(`[INFO] Memulai ekstraksi: ${totalRecord} data pada ${totalHalaman} halaman.`);
    
    let hasilEkstraksi = "";
    let jumlahTerekstrak = 0;
    
    // Menggunakan struktur data Set() sebagai validator Unique Key (Mencegah Redundansi Data)
    const setDataUnik = new Set();
    
    // 2. Iterasi Asynchronous: Melakukan perulangan untuk setiap halaman secara background
    for (let page = 1; page <= totalHalaman; page++) {
        console.log(`[PROSES] Mengunduh (Fetch) Halaman ${page}...`);
        
        // Memanipulasi parameter URL untuk navigasi halaman tanpa reload
        let url = new URL(window.location.href);
        url.searchParams.set("page", page);
        if(!url.searchParams.has("search_pi")) url.searchParams.set("search_pi", "");
        
        // Melakukan Asynchronous HTTP Fetch
        let response = await fetch(url.toString());
        let htmlText = await response.text();
        
        // Melakukan DOM Parsing secara virtual di dalam memori
        let parser = new DOMParser();
        let doc = parser.parseFromString(htmlText, "text/html");
        
        // Mengisolasi Node List dari seluruh tabel di dalam DOM
        let semuaTabel = doc.querySelectorAll('table.table-custom');
        
        // 3. Ekstraksi Data: Membedah baris dan sel pada tabel spesifik (Indeks 2)
        if (semuaTabel.length > 2) { 
            let barisTabel = semuaTabel[2].querySelectorAll('tr');
            
            barisTabel.forEach(baris => {
                let sel = baris.querySelectorAll('td');
                // Validasi jumlah kolom (Tabel PI memiliki 5 Kolom Aktif)
                if (sel.length >= 5) {
                    let kelas = sel[0].innerText.trim();
                    let kelompok = sel[1].innerText.trim();
                    let npm = sel[2].innerText.trim();
                    let nama = sel[3].innerText.trim();
                    let dosen = sel[4].innerText.trim();
                    
                    let uniqueKey = npm; // NPM digunakan sebagai Primary Key
                    
                    // Filter Logika: Hanya data unik yang akan diproses
                    if (!setDataUnik.has(uniqueKey)) {
                        setDataUnik.add(uniqueKey);
                        // String Interpolation untuk format Data Preparation (RAG Knowledge Base)
                        hasilEkstraksi += `${kelas}. Kelompok ${kelompok}, NPM: ${npm}, Nama: ${nama}, Pembimbing: ${dosen}\n`;
                        jumlahTerekstrak++;
                    }
                }
            });
        }
        
        // Implementasi Delay (Politeness Policy) untuk menghindari pemblokiran WAF / Anti-Bot
        await new Promise(resolve => setTimeout(resolve, 1500));
    }
    
    console.log(`[SELESAI] Total Data Terekstrak: ${jumlahTerekstrak} baris.`);
    
    // 4. Otomatisasi Export Data: Mengonversi memori teks menjadi file (.txt) via Blob
    if (jumlahTerekstrak > 0) {
        let blob = new Blob([hasilEkstraksi], { type: "text/plain;charset=utf-8" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `dataset_dosen_pi.txt`;
        document.body.appendChild(link);
        link.click(); // Trigger simulasi klik unduh
        document.body.removeChild(link);
    }
}

// Eksekusi Algoritma
ekstraksiDataTerpaginasi();
