// === SKRIP EKSTRAKSI DOM: ISOLASI TABEL & ANTI-DUPLIKAT (FINAL) ===

async function ekstrakSemuaHalaman() {
    let elemenTotal = document.querySelector('p b');
    let totalRecord = elemenTotal ? parseInt(elemenTotal.innerText.trim()) : 0;
    let totalHalaman = Math.ceil(totalRecord / 20);
    
    let hasilTeks = "";
    let jumlahTerekstrak = 0;
    
    // Fitur Baru: Set() untuk mencegah rekaman data ganda (Deduplikasi)
    let kelasUnik = new Set();
    let jumlahDuplikat = 0;
    
    for (let page = 1; page <= totalHalaman; page++) {
        console.log(`⏳ Mengekstrak Halaman ${page} dari ${totalHalaman}...`);
        
        let url = new URL(window.location.href);
        url.searchParams.set("page", page);
        
        let response = await fetch(url.toString());
        let htmlText = await response.text();
        
        let parser = new DOMParser();
        let doc = parser.parseFromString(htmlText, "text/html");
        let semuaTabel = doc.querySelectorAll('table.table-custom');
        
        if (semuaTabel.length > 0) {
            let tabelTarget = semuaTabel[0]; 
            let barisTabel = tabelTarget.querySelectorAll('tr');
            
            barisTabel.forEach(baris => {
                let sel = baris.querySelectorAll('td');
                if (sel.length >= 3) {
                    let no = sel[0].innerText.trim();
                    let kelas = sel[1].innerText.trim();
                    let dosen = sel[2].innerText.trim();
                    
                    // PENGECEKAN DUPLIKAT: Jika kelas belum ada di memori
                    if (!kelasUnik.has(kelas)) {
                        kelasUnik.add(kelas);
                        hasilTeks += `${no}. Kelas ${kelas}: ${dosen}\n`;
                        jumlahTerekstrak++;
                    } else {
                        // Jika terdeteksi ganda, catat log dan buang
                        jumlahDuplikat++;
                        console.warn(`⚠️ Ditemukan data ganda pada Kelas ${kelas}, otomatis dibuang!`);
                    }
                }
            });
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log(`✅ Selesai! Data unik terekstrak: ${jumlahTerekstrak} baris.`);
    if (jumlahDuplikat > 0) {
        console.log(`🧹 Telah membersihkan ${jumlahDuplikat} data ganda bawaan web.`);
    }
    
    if (jumlahTerekstrak > 0) {
        let blob = new Blob([hasilTeks], { type: "text/plain;charset=utf-8" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `daftar_dosen_kelas_${jumlahTerekstrak}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

ekstrakSemuaHalaman();
