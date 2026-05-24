# LAPORAN TEKNIS ANALISIS STRUKTUR DATASET

## 1. PENDAHULUAN
Laporan ini merinci struktur, skema, dan metodologi akses untuk ekosistem dataset yang terdiri dari dokumen tekstual (SIBI Books) dan representasi vektor (Embeddings) untuk kebutuhan sistem temu kembali informasi (Information Retrieval).

---

## 2. DATASET TEKSTUAL: `sibi_books.jsonl`
Dataset ini berfungsi sebagai *Source of Truth* yang menyimpan konten literatur dalam format terstruktur.

### 2.1. Atribut Utama (Primary Schema)
| Nama Kolom | Tipe Data | Deskripsi |
|---|---|---|
| `id` | String | Hash unik identifikasi dokumen. |
| `metadata` | Dictionary | Objek bersarang berisi atribut bibliografi. |
| `summary_text` | String | Representasi ringkas (sinopsis) konten. |
| `full_text` | String | Transkrip lengkap isi buku. |

### 2.2. Analisis Struktur Metadata (Nested Sub-keys)
Kolom `metadata` memiliki skema internal sebagai berikut:
| Sub-key | Tipe | Keterangan |
|---|---|---|
| `tipe` | str | Deskripsi atribut terkait tipe |
| `jenjang` | str | Deskripsi atribut terkait jenjang |
| `kelas` | str | Deskripsi atribut terkait kelas |
| `mata_pelajaran` | str | Deskripsi atribut terkait mata pelajaran |
| `judul_buku` | str | Deskripsi atribut terkait judul buku |
| `link_sampul` | str | Deskripsi atribut terkait link sampul |
| `link_sumber` | str | Deskripsi atribut terkait link sumber |
| `link_buku` | str | Deskripsi atribut terkait link buku |


---

## 3. DATASET VEKTOR: `rec_embeddings.jsonl`
Dataset ini merupakan derivasi dari dataset tekstual yang telah ditransformasi menjadi ruang vektor numerik.

### 3.1. Spesifikasi Model Embedding
- **Arsitektur Model**: `gemini-embedding-2`
- **Dimensi Vektor**: 3072
- **Tipe Tugas**: `RETRIEVAL_DOCUMENT`
- **Metrik Jarak**: Cosine Similarity / Inner Product

---

## 4. SISTEM INDEKSASI (FAISS INDEX)
Indeksasi dilakukan menggunakan pustaka FAISS untuk mendukung pencarian semantik berkecepatan tinggi.

### 4.1. `chunks_index.faiss` (Granularitas Paragraf)
- **Tipe Indeks**: `IndexFlatIP` (Flat Inner Product)
- **Kapasitas**: 2203 Vektor
- **Kegunaan**: Pencarian spesifik pada potongan teks (chunks).

### 4.2. `rec_index.faiss` (Granularitas Dokumen)
- **Tipe Indeks**: `IndexFlatIP`
- **Kapasitas**: 209 Vektor
- **Kegunaan**: Rekomendasi kemiripan antar buku secara holistik.

---

## 5. PEMETAAN METADATA (PICKLE STORAGE)
File `.pkl` menyimpan relasi antara indeks numerik FAISS dengan metadata asli buku.

- **Struktur Data**: Python Dictionary
- **Fungsi**: Mengonversi hasil pencarian FAISS (integer ID) kembali menjadi informasi yang dapat dibaca manusia (Judul, Link, dll).

---

## 6. PROTOKOL AKSES DATA (PYTHON IMPLEMENTATION)

### 6.1. Eksplorasi Data Relasional
```python
# Membaca dataset dengan optimasi memori
import pandas as pd
df = pd.read_json('sibi_books.jsonl', lines=True)
# Query metadata spesifik
sma_books = df[df['metadata'].map(lambda x: x.get('jenjang') == 'SMA/MA/SMK/MAK')]
```

### 6.2. Query Vektor pada FAISS
```python
import faiss
# Loading indeks biner
index = faiss.read_index('rec_index.faiss')
# Melakukan search (k=top results)
distances, indices = index.search(query_vector, k=5)
```
