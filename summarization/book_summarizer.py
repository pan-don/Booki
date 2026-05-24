import time
import random
import google.genai as genai
from google.genai import types

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from utils.logger import get_logger
from utils.api_key_manager import create_gemini_key_manager

logger = get_logger(__name__)
key_manager = create_gemini_key_manager()

def get_client() -> genai.Client:
    return genai.Client(api_key=key_manager.get_current_key() or "")

def call_gemini(prompt: str, temperature: float = 0.3) -> str:
    """
    Memanggil Gemini API dengan retry dan error handling yang robust dan key rotation.
    """
    client = get_client()
    
    max_retries_total = 5 * len(key_manager.keys)
    for attempt in range(max_retries_total):
        try:
            logger.debug(f"Calling Gemini (attempt {attempt+1}/{max_retries_total})")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
            )
        
            try:
                finish_reason = response.candidates[0].finish_reason
                # Check for STOP (often enum value 1 or "STOP")
                if finish_reason not in (1, "STOP"): 
                    logger.warning(f"Generation stopped abnormally. Reason ID: {finish_reason}")
            except Exception:
                pass

            if response.text:
                return response.text.strip()
            else:
                raise ValueError("Response text is empty")
                
        except Exception as e:
            error_msg = str(e)
            current_key = key_manager.get_current_key()
            logger.warning(f"Attempt {attempt+1} failed with key {current_key[:5]}... - msg: {error_msg}")
             
            if "429" in error_msg or "Resource exhausted" in error_msg or "quota" in error_msg.lower():
                key_manager.report_error(current_key, error_msg)
                new_key = key_manager.get_current_key()
                if new_key != current_key:
                    client = get_client()
                wait = 10 + random.uniform(0, 5)
                logger.warning(f"Rate limit or quota exceeded. Key rotated. Waiting {wait:.2f} seconds")
                time.sleep(wait)
                continue
            elif "timeout" in error_msg.lower():
                wait = 2 ** (attempt % 5) * 5
                logger.warning(f"Timeout. Waiting {wait}s")
                time.sleep(wait)
            else:
                wait = 2 ** (attempt % 5) * 3
                logger.warning(f"Other error. Waiting {wait}s")
                time.sleep(wait)
    
    raise Exception("Failed to get response from Gemini after all attempts")

def summarize_book(metadata: dict, combined_text: str) -> str:
    judul = metadata.get("judul_buku", "Buku tanpa judul")
    jenjang = metadata.get("jenjang", "")
    kelas = metadata.get("kelas", "")
    mapel = metadata.get("mata_pelajaran", "")

    prompt = f"""Anda adalah seorang peringkas buku teks profesional untuk Kurikulum Merdeka. Tugas Anda adalah membuat ringkasan yang informatif, komprehensif, dan mudah di-embed untuk sistem RAG.

Informasi Buku:
- Judul: {judul}
- Jenjang: {jenjang} Kelas {kelas}
- Mata Pelajaran: {mapel}

Petunjuk Ringkasan (ikuti dengan ketat):
1. Target panjang ringkasan adalah sekitar 300-400 kata dalam Bahasa Indonesia baku. Jelaskan setiap poin dengan mendalam dan deskriptif untuk mencapai target ini.
2. HARUS DIPARAFRASE MENGGUNAKAN BAHASA ANDA SENDIRI! DILARANG KERAS menyalin (copy-paste) kalimat asli dari teks secara verbatim/identik. Jika Anda mengutip, ubah struktur kalimatnya sepenuhnya untuk menghindari filter hak cipta/recitation.
3. Struktur ringkasan (buat dalam paragraf yang rapi):
   - Penjelasan Umum: Jabarkan secara mendalam tujuan pembelajaran utama, fokus materi, dan kompetensi/keterampilan yang ingin dicapai melalui buku ini.
   - Rincian Materi Pokok: Jelaskan 5-7 topik atau bab terpenting di dalam buku. Gunakan format bullet point (dengan tanda "-") dan berikan deskripsi atau ringkasan penjelasan untuk tiap topik tersebut (bukan sekadar menyebutkan nama bab).
   - Pendekatan Belajar & Gaya Penyajian: Deskripsikan bagaimana buku ini menyajikan materi. Jelaskan pemanfaatan elemen seperti narasi/cerita, ilustrasi, studi kasus, latihan soal, proyek berbasis aktivitas, atau refleksi. 
   - Analisis Kesulitan & Audiens: Jelaskan tingkat kesulitan materi serta karakteristik siswa yang paling cocok menggunakan buku ini berdasarkan muatan di dalamnya.
4. Ekstrak dan manfaatkan informasi sedetail mungkin dari teks sumber. Jangan menambahkan informasi di luar teks buku (jangan berasumsi atau berhalusinasi).
5. Hindari kalimat pembuka atau penutup yang basa-basi (seperti "Berdasarkan teks di atas..." atau "Ringkasan ini..."). Langsung masuk ke inti materi.

Teks Buku (gabungan dari beberapa bagian):
{combined_text[:40000]}

Ringkasan:
"""
    response = call_gemini(prompt, temperature=0.3)
    return response