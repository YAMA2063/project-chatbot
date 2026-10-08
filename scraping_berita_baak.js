const fs = require('fs');
const path = require('path');

const OUTPUT_FILE = path.join(__dirname, 'data preprocessing', 'berita_terbaru_baak.txt');
const START_ID = 758;
const COUNT = 10;

async function fetchNews() {
    console.log(`Mulai mengambil ${COUNT} berita terbaru dari BAAK...`);
    let allNews = "=== 10 BERITA TERBARU BAAK ===\n\n";

    for (let i = 0; i < COUNT; i++) {
        const id = START_ID - i;
        const url = `https://baak.gunadarma.ac.id/beritabaak/${id}`;
        try {
            console.log(`[${i+1}/${COUNT}] Mengambil berita ID ${id}...`);
            const response = await fetch(url);
            if (!response.ok) {
                console.log(`Gagal mengambil berita ID ${id}: HTTP ${response.status}`);
                continue;
            }
            const html = await response.text();

            // Ekstrak judul (h2, h3, atau elemen yang tampak seperti judul berita)
            // Di baak gunadarma, judul biasanya ada di dalam tag yang besar, atau title tag
            let title = "Judul Tidak Diketahui";
            const titleMatch = html.match(/<title>([^<]+)<\/title>/i);
            if (titleMatch) title = titleMatch[1].trim();
            
            // Coba ambil dari elemen text yang uppercase atau heading
            const h1Match = html.match(/<h[12][^>]*>(.*?)<\/h[12]>/is);
            if (h1Match) {
                // remove html tags from heading
                title = h1Match[1].replace(/<[^>]+>/g, '').trim();
            }

            // Ekstrak konten
            // Biasanya konten dibungkus dalam div tertentu. Kita bisa menggunakan ekspresi reguler
            // untuk mengambil teks setelah tanggal/admin.
            let content = "Konten tidak dapat diekstrak secara akurat menggunakan regex sederhana.";
            
            // Pendekatan kasar: Hapus semua script, style, head, nav, header, footer
            let cleanHtml = html
                .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ')
                .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ')
                .replace(/<nav\b[^<]*(?:(?!<\/nav>)<[^<]*)*<\/nav>/gi, ' ')
                .replace(/<header\b[^<]*(?:(?!<\/header>)<[^<]*)*<\/header>/gi, ' ')
                .replace(/<footer\b[^<]*(?:(?!<\/footer>)<[^<]*)*<\/footer>/gi, ' ');
            
            // Ambil body
            const bodyMatch = cleanHtml.match(/<body[^>]*>(.*?)<\/body>/is);
            if (bodyMatch) {
                cleanHtml = bodyMatch[1];
            }

            // Hapus HTML tags, replace br dan p dengan newline
            content = cleanHtml
                .replace(/<\/?(?:p|br|div|tr|li|ul|ol|h[1-6])[^>]*>/gi, '\n')
                .replace(/<[^>]+>/g, ' ')
                .replace(/&nbsp;/g, ' ')
                .replace(/\n\s*\n/g, '\n') // remove multiple newlines
                .replace(/ {2,}/g, ' ') // remove multiple spaces
                .trim();
            
            // Coba potong bagian atas dan bawah yang biasanya berisi menu dan footer
            // Berita BAAK biasanya dimulai dengan judul atau tanggal
            const lines = content.split('\n').map(l => l.trim()).filter(l => l.length > 0);
            
            // Cari indeks di mana judul atau 'Admin' muncul
            let startIndex = 0;
            let endIndex = lines.length;
            
            for (let j = 0; j < lines.length; j++) {
                if (lines[j].toLowerCase().includes('admin') || lines[j].includes(title)) {
                    startIndex = j;
                    break;
                }
            }
            
            // Buang baris setelah kata-kata copyright atau footer
            for (let j = lines.length - 1; j >= 0; j--) {
                if (lines[j].toLowerCase().includes('copyright') || lines[j].toLowerCase().includes('all rights reserved')) {
                    endIndex = j;
                    break;
                }
            }
            
            let finalContent = lines.slice(startIndex, endIndex).join('\n');
            if (finalContent.length < 20) {
                finalContent = content; // fallback
            }

            allNews += `-------------------------------------------------\n`;
            allNews += `ID BERITA : ${id}\n`;
            allNews += `URL       : ${url}\n`;
            allNews += `JUDUL     : ${title}\n`;
            allNews += `-------------------------------------------------\n`;
            allNews += `${finalContent}\n\n`;

        } catch (error) {
            console.error(`Error mengambil berita ID ${id}:`, error.message);
        }
    }

    fs.writeFileSync(OUTPUT_FILE, allNews, 'utf8');
    console.log(`\nSelesai! Berita berhasil disimpan ke: ${OUTPUT_FILE}`);
}

fetchNews();
