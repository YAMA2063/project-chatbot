// === SCRIPT EKSTRAKSI JADWAL UJIAN UTAMA ===
async function ekstrakJadwalUjian() {
    // 1. Ambil semua opsi jurusan dari elemen Select (Dropdown)
    let options = Array.from(document.querySelectorAll('select[name="jurusan"] option'))
                       .map(o => o.value)
                       .filter(v => v !== "");
    
    console.log(`[INFO] Memulai ekstraksi jadwal ujian untuk total ${options.length} jurusan.`);
    
    let hasilEkstraksi = "";
    let jumlahTerekstrak = 0;
    
    for (let i = 0; i < options.length; i++) {
        let jurusan = options[i];
        console.log(`[PROSES] Mencari jadwal ujian jurusan ${jurusan} (${i+1}/${options.length})...`);
        
        let url = new URL("https://baak.gunadarma.ac.id/jadwal/cariUtama");
        url.searchParams.set("jurusan", jurusan);
        
        try {
            let response = await fetch(url.toString());
            
            if (response.status === 403) {
                console.error(`🚨 ALERT: Diblokir Cloudflare di jurusan ${jurusan}!`);
                break; // Hentikan loop jika diblokir
            }
            
            let htmlText = await response.text();
            let parser = new DOMParser();
            let doc = parser.parseFromString(htmlText, "text/html");
            
            // Cari tabel jadwal. BAAK biasanya pakai table-custom
            let semuaTabel = doc.querySelectorAll('table');
            let adaJadwal = false;

            semuaTabel.forEach(tabel => {
                let barisTabel = tabel.querySelectorAll('tr');
                if(barisTabel.length > 1) {
                    barisTabel.forEach(baris => {
                        let sel = baris.querySelectorAll('td');
                        
                        // Kolom Jadwal Ujian BAAK: 0=No, 1=Hari, 2=Tanggal, 3=Waktu, 4=Mata Kuliah, 5=Ruang
                        if (sel.length >= 6) {
                            let hari = sel[1].innerText.trim();
                            let tanggal = sel[2].innerText.trim();
                            let waktu = sel[3].innerText.trim();
                            let matkul = sel[4].innerText.trim();
                            let ruang = sel[5].innerText.trim() || "-";
                            
                            // Abaikan baris header atau data kosong
                            if (hari !== "" && hari.toLowerCase() !== "hari" && matkul !== "") {
                                hasilEkstraksi += `Jurusan: ${jurusan}, Hari: ${hari}, Tanggal: ${tanggal}, Waktu: ${waktu}, Mata Kuliah: ${matkul}, Ruang: ${ruang}\n`;
                                adaJadwal = true;
                                jumlahTerekstrak++;
                            }
                        }
                    });
                }
            });

            if (adaJadwal) {
                console.log(`✅ Ketemu jadwal ujian untuk ${jurusan}`);
            } else {
                console.log(`⚠️ Tidak ada jadwal untuk ${jurusan}`);
            }

        } catch (e) {
            console.error("Gagal fetch:", e);
        }
        
        // Jeda waktu (2 detik) agar tidak dicurigai Cloudflare
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    console.log(`[SELESAI] Total Jadwal Ujian Terekstrak: ${jumlahTerekstrak} baris.`);
    
    if (jumlahTerekstrak > 0) {
        let blob = new Blob([hasilEkstraksi], { type: "text/plain;charset=utf-8" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "dataset_jadwal_ujian_utama.txt";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// EKSEKUSI
ekstrakJadwalUjian();
