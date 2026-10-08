// === SKRIP EKSTRAKSI KHUSUS: KOORDINATOR MATA KULIAH (FORMAT RAPI) ===

async function ekstrakKoordinatorMatkul() {
    let semuaTotal = document.querySelectorAll('p b');
    
    // Pastikan angka yang diambil adalah angka milik Koordinator Matkul (Index 1)
    let totalRecord = semuaTotal.length > 1 ? parseInt(semuaTotal[1].innerText.trim()) : 0;
    let totalHalaman = Math.ceil(totalRecord / 20);
    
    console.log(`🎯 Target dikunci: ${totalRecord} data Koordinator Matkul (${totalHalaman} Halaman).`);
    
    let hasilTeks = "";
    let jumlahTerekstrak = 0;
    let dataUnik = new Set();
    
    for (let page = 1; page <= totalHalaman; page++) {
        console.log(`⏳ Menyedot Halaman ${page} dari ${totalHalaman}...`);
        
        let url = new URL(window.location.href);
        url.searchParams.set("page", page);
        
        let response = await fetch(url.toString());
        let htmlText = await response.text();
        
        let parser = new DOMParser();
        let doc = parser.parseFromString(htmlText, "text/html");
        
        let semuaTabel = doc.querySelectorAll('table.table-custom');
        
        if (semuaTabel.length > 1) { 
            let tabelTarget = semuaTabel[1]; // TABEL KOORDINATOR
            let barisTabel = tabelTarget.querySelectorAll('tr');
            
            barisTabel.forEach(baris => {
                let sel = baris.querySelectorAll('td');
                if (sel.length >= 4) {
                    let no = sel[0].innerText.trim();
                    let matkul = sel[1].innerText.trim();
                    let kelas = sel[2].innerText.trim();
                    let dosen = sel[3].innerText.trim();
                    
                    let uniqueKey = matkul + "_" + kelas;
                    
                    if (!dataUnik.has(uniqueKey)) {
                        dataUnik.add(uniqueKey);
                        // PERBAIKAN FORMAT: Menggunakan Koma sesuai standar file asli Anda
                        hasilTeks += `${no}. Mata Kuliah: ${matkul}, Kelas: ${kelas}, Dosen: ${dosen}\n`;
                        jumlahTerekstrak++;
                    }
                }
            });
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log(`✅ Selesai! Data berhasil diekstrak: ${jumlahTerekstrak} baris.`);
    
    if (jumlahTerekstrak > 0) {
        let blob = new Blob([hasilTeks], { type: "text/plain;charset=utf-8" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `daftar_koordinator_matkul.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

ekstrakKoordinatorMatkul();
