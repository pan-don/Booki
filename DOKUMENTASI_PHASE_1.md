# 📄 Dokumentasi Perubahan Sistem: Phase 1 (Isolasi Infrastruktur & Keamanan Jaringan)

## Latar Belakang & Spesifikasi Isolasi Infrastruktur

Sistem rekomendasi buku ini kini telah dipisahkan menjadi **arsitektur ter-decoupled**:
- **Backend (Flask RAG Engine)**: Dideploy ke Hugging Face Spaces.
- **Frontend UI (Next.js + TypeScript)**: Dideploy ke Cloudflare Pages.

Pemisahan ini memerlukan standar keamanan tinggi untuk manajemen konsumsi API dan kontrol origin (CORS). Kami membagi total 17 lisensi (API Keys) dari Gemini ke dalam dua (2) kelompok beban kerja terisolasi. Hal ini ditujukan untuk mencegah "Cross-Workload Exhaustion", yaitu kondisi di mana proses ekstraksi (ingestion) yang masif menghabiskan limit akses dan menyebabkan fitur tanya-jawab chatbot secara real-time gagal total.

- **Pool Embedding (Keys 1-10):** Mengatur beban komputasi konversi teks (ingestion & summarization vector).
- **Pool QA (Keys 11-17):** Mengatur sesi chatbot yang asinkron dari pengguna akhir secara interaktif.

## Tabel Peta Variabel Lingkungan (.env)

Berikut adalah environment variable yang wajib dikonfigurasikan agar sistem Backend berhasil menyala pada Hugging Face Spaces tanpa _Error 500_:

| Nama Variabel | Deskripsi Nilai | Target Alokasi |
| ------------- | ------------- | ------------- |
| `FRONTEND_URL` | URL absolut untuk produksi Frontend (Misal: `https://frontend.cloudflare.pages.dev`). Opsional _fallback_ ke `http://localhost:3000` di lingkungan lokal. | Kontrak Keamanan (CORS) |
| `GEMINI_API_KEY_1` s/d `GEMINI_API_KEY_10` | Kunci API Google Gemini untuk konversi data. | Pool Embedding (Ingestion) |
| `GEMINI_API_KEY_11` s/d `GEMINI_API_KEY_17` | Kunci API Google Gemini untuk chat langsung. | Pool Tanya Jawab (QA/Chat) |
| `GEMINI_MODEL` | Model Default untuk Chatbot (Misal: `gemini-2.5-flash`) | Engine QA |
| `EMBEDDING_MODEL` | Model Default untuk Embedding (Misal: `gemini-embedding-2`) | Engine Embedding |

## Kontrak Komunikasi Lintas Repositori (CORS Spec)

Untuk Frontend Engineering (Cloudflare Pages), **wajib** menyesuaikan fetch/axios pre-flight headers dengan aturan ketat berikut karena Backend (Hugging Face Spaces) tidak lagi menerima request *wildcard*:

1. **Origins Terdaftar**: Request hanya akan diterima jika asal domain (`Origin`) cocok dengan environment variable `FRONTEND_URL` di Backend.
2. **HTTP Methods yang Diizinkan**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`. (Metode `OPTIONS` wajib disetujui di sisi frontend jika melakukan custom fetch proxy).
3. **HTTP Headers yang Diizinkan**: `Content-Type`, `Authorization`.

**Tips Implementasi Frontend (Contoh Fetch API)**:
```javascript
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/recommend`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    // 'Authorization': 'Bearer <token>' // (Jika diperlukan di masa mendatang)
  },
  body: JSON.stringify({ query: "Saya butuh buku matematika" })
});
```

Pastikan tidak ada _custom header_ lain selain yang di whitelist di atas tanpa request _pull request_ tambahan ke repository backend.
