// === MASTER SCRIPT: EKSTRAKSI JADWAL UJIAN AKHIR SEMESTER (UAS) ===

async function ekstrakJadwalUAS() {
    // 1. DAFTAR KELAS AKTIF (Diambil langsung dari Jadwal Kuliah)
    const semuaKelas = ["1DA01", "1DB01", "1DC01", "1DD01", "1DF01", "1EA01", "1EA02", "1EA03", "1EA04", "1EA05", "1EA06", "1EA07", "1EA08", "1EA09", "1EA10", "1EA11", "1EA12", "1EA13", "1EA14", "1EA15", "1EA16", "1EA17", "1EA18", "1EA19", "1EA20", "1EA21", "1EA22", "1EA23", "1EA24", "1EA25", "1EA26", "1EA27", "1EA28", "1EA29", "1EA30", "1EA31", "1EA32", "1EB01", "1EB02", "1EB03", "1EB04", "1EB05", "1EB06", "1EB07", "1EB08", "1EB09", "1EB10", "1EB11", "1EB12", "1EB13", "1EB14", "1EB15", "1EB16", "1EB17", "1EB18", "1EB19", "1EC01", "1EC02", "1HB01", "1HB02", "1HB03", "1HC01", "1IA01", "1IA02", "1IA03", "1IA04", "1IA05", "1IA06", "1IA07", "1IA08", "1IA09", "1IA10", "1IA11", "1IA12", "1IA13", "1IA14", "1IA15", "1IA16", "1IA17", "1IB01", "1IB02", "1IB03", "1IB04", "1IB05", "1IC01", "1IC02", "1IC03", "1IC04", "1IC05", "1ID01", "1ID02", "1ID03", "1ID04", "1ID05", "1ID06", "1ID07", "1ID08", "1ID09", "1ID10", "1ID11", "1ID12", "1ID13", "1IE01", "1IE02", "1KA01", "1KA02", "1KA03", "1KA04", "1KA05", "1KA06", "1KA07", "1KA08", "1KA09", "1KA10", "1KA11", "1KA12", "1KA13", "1KA14", "1KA15", "1KA16", "1KA17", "1KA18", "1KA19", "1KA20", "1KA21", "1KA22", "1KA23", "1KA24", "1KA25", "1KA26", "1KA27", "1KA28", "1KA29", "1KB01", "1KB02", "1KB03", "1KB04", "1KB05", "1KB06", "1MA01", "1MA02", "1MA03", "1MA04", "1MA05", "1MA06", "1MA07", "1MA08", "1MA09", "1MA10", "1MA11", "1MA12", "1MA13", "1MA14", "1MA15", "1MA16", "1MA17", "1MA18", "1MA19", "1MA20", "1MA21", "1MA22", "1MA23", "1MA24", "1MA25", "1MA26", "1MA27", "1MA28", "1MA29", "1PA01", "1PA02", "1PA03", "1PA04", "1PA05", "1PA06", "1PA07", "1PA08", "1PA09", "1PA10", "1PA11", "1PA12", "1PA13", "1PA14", "1PA15", "1PA16", "1PA17", "1PA18", "1PA19", "1PA20", "1PA21", "1PA22", "1PA23", "1PA24", "1PA25", "1PA26", "1PA27", "1PA28", "1PA29", "1SA01", "1SA02", "1SA03", "1SA04", "1SA05", "1SA06", "1SB01", "1SB02", "1SB03", "1SC01", "1SC02", "1SC03", "1TA01", "1TA02", "1TA03", "1TA04", "1TA05", "1TB01", "1TB02", "1TB03", "1TB04", "1TC01", "1TC02", "1TC03", "2DA01", "2DA02", "2DB01", "2DC01", "2DC02", "2DD01", "2DD02", "2DF01", "2DF02", "2EA01", "2EA02", "2EA03", "2EA04", "2EA05", "2EA06", "2EA07", "2EA08", "2EA09", "2EA10", "2EA11", "2EA12", "2EA13", "2EA14", "2EA15", "2EA16", "2EA17", "2EA18", "2EA19", "2EA20", "2EA21", "2EA22", "2EA23", "2EA24", "2EA25", "2EA26", "2EA27", "2EA28", "2EA29", "2EA30", "2EA31", "2EA32", "2EA33", "2EA34", "2EA35", "2EA36", "2EA37", "2EA38", "2EB01", "2EB02", "2EB03", "2EB04", "2EB05", "2EB06", "2EB07", "2EB08", "2EB09", "2EB10", "2EB11", "2EB12", "2EB13", "2EB14", "2EB15", "2EB16", "2EB17", "2EB18", "2EB19", "2EC01", "2HB01", "2HB02", "2HB03", "2IA01", "2IA02", "2IA03", "2IA04", "2IA05", "2IA06", "2IA07", "2IA08", "2IA09", "2IA10", "2IA11", "2IA12", "2IA13", "2IA14", "2IA15", "2IA16", "2IA17", "2IA18", "2IA19", "2IA20", "2IA21", "2IA22", "2IB01", "2IB02", "2IB03", "2IB04", "2IC01", "2IC02", "2IC03", "2IC04", "2IC05", "2IC06", "2ID01", "2ID02", "2ID03", "2ID04", "2ID05", "2ID06", "2ID07", "2ID08", "2ID09", "2ID10", "2ID11", "2IE01", "2KA01", "2KA02", "2KA03", "2KA04", "2KA05", "2KA06", "2KA07", "2KA08", "2KA09", "2KA10", "2KA11", "2KA12", "2KA13", "2KA14", "2KA15", "2KA16", "2KA17", "2KA18", "2KA19", "2KA20", "2KA21", "2KA22", "2KA23", "2KA24", "2KA26", "2KA27", "2KA28", "2KA29", "2KA30", "2KA31", "2KA32", "2KA33", "2KA34", "2KB01", "2KB02", "2KB03", "2KB04", "2KB05", "2MA01", "2MA02", "2MA03", "2MA04", "2MA05", "2MA06", "2MA07", "2MA08", "2MA09", "2MA10", "2MA11", "2MA12", "2MA13", "2MA14", "2MA15", "2MA16", "2MA17", "2MA18", "2MA19", "2MA20", "2MA21", "2MA22", "2MA23", "2MA24", "2MA25", "2MA26", "2MA27", "2MA28", "2MA29", "2MA30", "2PA01", "2PA02", "2PA03", "2PA04", "2PA05", "2PA06", "2PA07", "2PA08", "2PA09", "2PA10", "2PA11", "2PA12", "2PA13", "2PA14", "2PA15", "2PA16", "2PA17", "2PA18", "2PA19", "2PA20", "2PA21", "2PA22", "2PA23", "2PA24", "2PA25", "2PA26", "2PA27", "2PA28", "2PA29", "2PA30", "2PA31", "2PA32", "2PA33", "2PA34", "2PA35", "2SA01", "2SA02", "2SA03", "2SA04", "2SA05", "2SA06", "2SB01", "2SB02", "2SB03", "2SC01", "2SC02", "2TA01", "2TA02", "2TA03", "2TA04", "2TA05", "2TB01", "2TB02", "2TB03", "2TB04", "2TC01", "2TC02", "2TC03", "3DA01", "3DA02", "3DB01", "3DC01", "3DC02", "3DD01", "3DD02", "3DF01", "3DF02", "3EA01", "3EA02", "3EA03", "3EA04", "3EA05", "3EA06", "3EA07", "3EA08", "3EA09", "3EA10", "3EA11", "3EA12", "3EA13", "3EA14", "3EA15", "3EA16", "3EA17", "3EA18", "3EA19", "3EA20", "3EA21", "3EA22", "3EA23", "3EA24", "3EA25", "3EA26", "3EA27", "3EA28", "3EA29", "3EA30", "3EA31", "3EA32", "3EA33", "3EA34", "3EA35", "3EA36", "3EA37", "3EB01", "3EB02", "3EB03", "3EB04", "3EB05", "3EB06", "3EB07", "3EB08", "3EB09", "3EB10", "3EB11", "3EB12", "3EB13", "3EB14", "3EB15", "3EB16", "3EB17", "3EB18", "3HB01", "3HB02", "3HC01", "3HC02", "3IA01", "3IA02", "3IA03", "3IA04", "3IA05", "3IA06", "3IA07", "3IA08", "3IA10", "3IA11", "3IA12", "3IA13", "3IA14", "3IA15", "3IA16", "3IA17", "3IA18", "3IA19", "3IA20", "3IA21", "3IA22", "3IA23", "3IA24", "3IA25", "3IA26", "3IB01", "3IB02", "3IB03", "3IC01", "3IC02", "3IC03", "3IC04", "3ID01", "3ID02", "3ID03", "3ID04", "3ID05", "3ID06", "3ID07", "3ID08", "3ID09", "3ID10", "3ID11", "3IF01", "3KA01", "3KA02", "3KA03", "3KA04", "3KA05", "3KA06", "3KA07", "3KA08", "3KA09", "3KA10", "3KA11", "3KA12", "3KA13", "3KA14", "3KA15", "3KA16", "3KA17", "3KA18", "3KA19", "3KA20", "3KA21", "3KA22", "3KA23", "3KA24", "3KA25", "3KA26", "3KA27", "3KA28", "3KA29", "3KA30", "3KA31", "3KA32", "3KA33", "3KA34", "3KA35", "3KB01", "3KB02", "3KB03", "3KB04", "3KB05", "3KC01", "3MA01", "3MA02", "3MA03", "3MA04", "3MA05", "3MA06", "3MA07", "3MA08", "3MA09", "3MA10", "3MA11", "3MA12", "3MA13", "3MA14", "3MA15", "3MA16", "3MA17", "3MA18", "3MA19", "3MA20", "3MA21", "3MA22", "3MA23", "3MA24", "3MA25", "3MA26", "3MA27", "3MA28", "3MA29", "3PA01", "3PA02", "3PA03", "3PA04", "3PA05", "3PA06", "3PA07", "3PA08", "3PA09", "3PA10", "3PA11", "3PA12", "3PA13", "3PA14", "3PA15", "3PA16", "3PA17", "3PA18", "3PA19", "3PA20", "3PA21", "3PA22", "3PA23", "3PA24", "3PA25", "3PA26", "3PA27", "3PA28", "3PA29", "3PA30", "3PA31", "3PA32", "3PA33", "3PA34", "3PA35", "3PA36", "3PB01", "3SA01", "3SA02", "3SA03", "3SA04", "3SA05", "3SA06", "3SA07", "3SB01", "3SC01", "3TA01", "3TA02", "3TA03", "3TA04", "3TA05", "3TB01", "3TB02", "3TB03", "3TB04", "3TC01", "3TD01", "3TE01", "4EA01", "4EA02", "4EA03", "4EA04", "4EA05", "4EA06", "4EA07", "4EA08", "4EA09", "4EA10", "4EA11", "4EA12", "4EA13", "4EA14", "4EA15", "4EA16", "4EA17", "4EA18", "4EA19", "4EA20", "4EA21", "4EA22", "4EA23", "4EA24", "4EA25", "4EA26", "4EA27", "4EA28", "4EA29", "4EA30", "4EA31", "4EA32", "4EA33", "4EA34", "4EA35", "4EA36", "4EA37", "4EA38", "4EA39", "4EA40", "4EB01", "4EB02", "4EB03", "4EB04", "4EB05", "4EB06", "4EB07", "4EB08", "4EB09", "4EB10", "4EB11", "4EB12", "4EB13", "4EB14", "4EB15", "4EB16", "4HB01", "4HB02", "4IA01", "4IA02", "4IA03", "4IA04", "4IA05", "4IA06", "4IA07", "4IA08", "4IA09", "4IA10", "4IA11", "4IA12", "4IA13", "4IA14", "4IA15", "4IA16", "4IA17", "4IA18", "4IA19", "4IA20", "4IA21", "4IA22", "4IA23", "4IA24", "4IA25", "4IA26", "4IA27", "4IA28", "4IB01", "4IB02", "4IB03", "4IC01", "4IC02", "4IC03", "4IC04", "4IC05", "4ID01", "4ID02", "4ID03", "4ID04", "4ID05", "4ID06", "4ID07", "4ID08", "4ID09", "4KA01", "4KA02", "4KA03", "4KA04", "4KA05", "4KA06", "4KA07", "4KA08", "4KA09", "4KA10", "4KA11", "4KA12", "4KA13", "4KA14", "4KA15", "4KA16", "4KA17", "4KA18", "4KA19", "4KA20", "4KA21", "4KA22", "4KA23", "4KA24", "4KA25", "4KA26", "4KA27", "4KA28", "4KA29", "4KA30", "4KA31", "4KA32", "4KA33", "4KA34", "4KA35", "4KA36", "4KB01", "4KB02", "4KB03", "4KB04", "4KB05", "4MA01", "4MA02", "4MA03", "4MA04", "4MA05", "4MA06", "4MA07", "4MA08", "4MA09", "4MA10", "4MA11", "4MA12", "4MA13", "4MA14", "4MA15", "4MA16", "4MA17", "4MA18", "4MA19", "4MA20", "4MA21", "4MA22", "4MA23", "4MA24", "4MA25", "4MA26", "4MA27", "4MA28", "4MA29", "4MA30", "4MA31", "4MA32", "4MA33", "4MA34", "4MA35", "4MA36", "4MA37", "4MA38", "4MA39", "4PA01", "4PA02", "4PA03", "4PA04", "4PA05", "4PA06", "4PA07", "4PA08", "4PA09", "4PA10", "4PA11", "4PA12", "4PA13", "4PA14", "4PA15", "4PA16", "4PA17", "4PA18", "4PA19", "4PA20", "4PA21", "4PA22", "4PA23", "4PA24", "4PA25", "4PA26", "4PA27", "4PA28", "4PA29", "4PA30", "4PA31", "4PA32", "4PA33", "4PA34", "4PA35", "4PA36", "4PA37", "4PA38", "4PA39", "4PA40", "4PA41", "4PA42", "4SA01", "4SA02", "4SA03", "4SA04", "4SA05", "4SA06", "4SA07", "4SA08", "4SA09", "4SA10", "4SB01", "4SC01", "4TA01", "4TA02", "4TA03", "4TA04", "4TA05", "4TA06", "4TB01", "4TB02", "4TB03", "4TB04", "4TB05"];

    // UBAH ANGKA INI UNTUK MELANJUTKAN JIKA DIBLOKIR CLOUDFLARE
    let startIndex = 590;

    console.log(`[INFO] Memulai ekstraksi jadwal UAS untuk total ${semuaKelas.length} kelas aktif (Dimulai dari urutan ke-${startIndex})`);

    let hasilEkstraksi = "";
    let jumlahTerekstrak = 0;

    let tokenForm = document.querySelector('input[name="_token"]');
    let csrfToken = tokenForm ? tokenForm.value : "";

    for (let i = startIndex; i < semuaKelas.length; i++) {
        let kelas = semuaKelas[i];
        console.log(`[PROSES] Mencari jadwal UAS kelas ${kelas} (${i + 1}/${semuaKelas.length})...`);

        let formData = new URLSearchParams();
        if (csrfToken) formData.append("_token", csrfToken);
        formData.append("teks", kelas);

        try {
            let response = await fetch("https://baak.gunadarma.ac.id/jadwal/cariUas", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData.toString()
            });

            if (response.status === 403) {
                console.error(`🚨 ALERT: Diblokir Cloudflare di kelas ${kelas}! Berhenti sejenak.`);
                break;
            }

            let htmlText = await response.text();
            let parser = new DOMParser();
            let doc = parser.parseFromString(htmlText, "text/html");

            let semuaTabel = doc.querySelectorAll('table');
            let adaJadwal = false;

            semuaTabel.forEach(tabel => {
                let barisTabel = tabel.querySelectorAll('tr');
                if (barisTabel.length > 1) {
                    barisTabel.forEach(baris => {
                        let sel = baris.querySelectorAll('td');
                        if (sel.length >= 4) {
                            let hari = sel[0].innerText.trim();
                            let tanggal = sel[1].innerText.trim();
                            let matkul = sel[2].innerText.trim();
                            let waktu = sel[3].innerText.trim();

                            if (hari !== "" && hari.toLowerCase() !== "hari" && matkul !== "") {
                                hasilEkstraksi += `Kelas: ${kelas}, Hari: ${hari}, Tanggal: ${tanggal}, Waktu: ${waktu}, Mata Kuliah: ${matkul}\n`;
                                adaJadwal = true;
                                jumlahTerekstrak++;
                            }
                        }
                    });
                }
            });

            if (adaJadwal) console.log(`✅ Ketemu jadwal UAS untuk ${kelas}`);

        } catch (e) {
            console.error("Gagal fetch:", e);
        }

        await new Promise(resolve => setTimeout(resolve, 2500));
    }

    console.log(`[SELESAI] Total Jadwal UAS Terekstrak: ${jumlahTerekstrak} baris.`);

    if (jumlahTerekstrak > 0) {
        let blob = new Blob([hasilEkstraksi], { type: "text/plain;charset=utf-8" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "dataset_jadwal_uas.txt";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

ekstrakJadwalUAS();
