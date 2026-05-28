"""
Answer Generator using Gemini API (LLM).
Generates final answers for recommendations or detailed questions.
Custom prompt ensures friendly, cheerful, and easy-to-understand responses in Indonesian.
"""

import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging

from config.settings import GEMINI_API_KEY, ANSWER_MODEL
from utils.logger import get_logger
from utils.api_key_manager import APIKeyManager

logger = get_logger(__name__)

# Default system prompt untuk personalisasi LLM
DEFAULT_SYSTEM_PROMPT = """
Anda adalah asisten pintar untuk Sistem Rekomendasi & Eksplorasi Buku Pelajaran. Anda sangat ramah, suportif, kreatif, ceria, dan menyenangkan! Gaya bahasa Anda disesuaikan untuk anak-anak sekolah dan remaja (SD, SMP, SMA).
Gunakan bahasa Indonesia yang baku namun santai, selipkan pujian penyemangat (contoh: "Wah, pertanyaan yang bagus sekali, Sobat Belajar!"), dan gunakan emoticon sewajarnya (seperti 📚, ✨, 🚀, 😊) untuk menghidupkan suasana.

ATURAN PENTING (GUARDRAILS):
1. Fokus hanya pada materi pendidikan, buku pelajaran, ilmu pengetahuan, dan rekomendasi bahan bacaan.
2. TOLAK SECARA HALUS DAN TEGAS jika pertanyaan pengguna:
   - Tidak relevan dengan dunia pendidikan atau buku pelajaran.
   - Mengandung unsur SARA (Suku, Agama, Ras, dan Antargolongan).
   - Terkait dengan politik, kekerasan, pornografi, peretasan, atau hal-hal negatif lainnya.
   - Bersifat provokasi, cyberbullying, atau berkata kasar.
   Cara Menolak: "Maaf ya, teman! Aku dirancang khusus untuk membantu kamu mengeksplorasi buku pelajaran dan ilmu pengetahuan. Yuk, kita kembali bahas buku atau materi sekolah saja! 📚✨"
3. Jangan pernah berhalusinasi. Jika informasi / jawaban tidak terdapat dalam konteks yang diberikan, beritahu pengguna dengan jujur bahwa informasinya tidak ada pada buku tersebut.
4. Jawab pertanyaan dengan rapi menggunakan paragraf pendek atau poin-poin agar mudah dibaca oleh pelajar.
"""

class AnswerGenerator:
    """
    Generates answers using Google Gemini API.
    """
    
    def __init__(
        self,
        api_key_manager: Optional[APIKeyManager] = None,
        model: str = ANSWER_MODEL,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """
        Initialize answer generator.
        
        Args:
            api_key_manager: APIKeyManager instance for Gemini keys.
            model: Model identifier (e.g., "gemini-3.1-flash-lite-preview").
            system_prompt: System prompt for the LLM.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in response.
        """
        self.api_key_manager = api_key_manager or APIKeyManager(GEMINI_API_KEY, service_name="Gemini")
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        genai.configure(api_key=self.api_key_manager.get_current_key())
        self.client = genai.GenerativeModel(self.model)
        
        logger.info(f"AnswerGenerator initialized with model {model}")
    
    def _call_gemini(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Make API call to Gemini.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
        
        Returns:
            Generated text or None if error.
        """
        try:
            # Gabungkan system prompt dan user prompt
            full_prompt = self.system_prompt + "\n\n" + messages[-1]['content']
            
            # Configure with the latest API key from rotation
            genai.configure(api_key=self.api_key_manager.get_current_key())
            client = genai.GenerativeModel(self.model)
            
            response = client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": self.temperature, 
                    "max_output_tokens": self.max_tokens
                }
            )
            if not response.text:
                logger.warning("Empty response from Gemini")
                return None
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            # Rotate key jika perlu
            self.api_key_manager.report_error(self.api_key_manager.get_current_key(), str(e))
            return None
    
    def generate_recommendation(
        self,
        user_query: str,
        retrieved_books: List[Dict[str, Any]]
    ) -> str:
        """
        Generate recommendation answer based on retrieved books.
        
        Args:
            user_query: User's preference query.
            retrieved_books: List of books from retriever+reranker (each dict contains title, summary, etc.)
        
        Returns:
            Generated recommendation text.
        """
        if not retrieved_books:
            return "Maaf, saya belum bisa menemukan buku yang sesuai dengan preferensimu. Coba berikan detail lebih spesifik ya! 😊"
        
        # Build context from retrieved books
        books_context = []
        for idx, book in enumerate(retrieved_books, start=1):
            title = book.get('title', 'Tanpa Judul')
            summary = book.get('summary_text', book.get('text', 'Tidak ada ringkasan'))
            mata_pelajaran = book.get('mata_pelajaran', 'Umum')
            jenjang = book.get('jenjang', '')
            kelas = book.get('kelas', '')
            level_info = f" ({jenjang} {kelas})" if jenjang or kelas else ""
            
            books_context.append(
                f"{idx}. **{title}**{level_info} - Mata pelajaran: {mata_pelajaran}\n"
                f"   Ringkasan: {summary[:500]}...\n"
            )
        
        context_str = "\n".join(books_context)
        
        user_prompt = f"""
Konteks buku yang direkomendasikan secara logis oleh sistem:

{context_str}

Pertanyaan/preferensi pengguna: "{user_query}"

Berdasarkan data di atas, berikan kalimat pengantar dan perbincangan naratif yang ramah, analitis, dan ceria.
Sertakan alasan ringkas mengapa buku-buku ini direkomendasikan.
DO NOT write rigid structural lists, bullet points, or repetitive metadata blocks for the books.
The UI will render the structured list natively. Your job is ONLY to provide the conversational, engaging chat text.
Gunakan bahasa Indonesia yang santai, selipkan emoji yang relevan seperti 📚, ✨, 😊.
"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._call_gemini(messages)
        if response is None:
            # Fallback response
            return "Maaf, layanan sedang sibuk. Coba lagi nanti ya! 📚✨"
        return response
    
    def generate_deep_answer(
        self,
        user_question: str,
        selected_books: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate detailed answer from fulltext chunks for a specific book or books.
        
        Args:
            user_question: Detailed user question about book content.
            selected_books: List of books the user chose (metadata).
            retrieved_chunks: List of relevant chunks from fulltext index (after reranking).
        
        Returns:
            Detailed answer with citations.
        """
        if not retrieved_chunks:
            # If no chunks found, inform user
            book_titles = ", ".join([b.get('title', 'Buku') for b in selected_books])
            return f"Wah, saya belum menemukan informasi spesifik tentang pertanyaanmu di dalam buku {book_titles}. Coba tanyakan hal lain atau pilih buku yang berbeda ya! 😊"
        
        # Build context from retrieved chunks
        chunks_context = []
        for idx, chunk in enumerate(retrieved_chunks[:5], start=1):  # limit to top 5 chunks
            chunk_text = chunk.get('chunk_text', '')
            book_title = chunk.get('title', 'Buku')
            page = chunk.get('page', 'halaman tidak diketahui')
            chunks_context.append(
                f"Sumber: Buku \"{book_title}\" ({page})\n"
                f"Kutipan: {chunk_text[:800]}...\n"
            )
        
        context_str = "\n".join(chunks_context)
        book_list_str = ", ".join([b.get('title', 'Buku') for b in selected_books])
        
        user_prompt = f"""
Pengguna memilih buku berikut: {book_list_str}
Pertanyaan detail: "{user_question}"

Berikut potongan informasi dari buku-buku tersebut yang relevan:
{context_str}

Jawablah pertanyaan pengguna dengan detail, jelas, dan mudah dipahami. 
Sebutkan dari buku mana informasi itu berasal (dan halaman jika ada). 
Jika informasi tidak cukup untuk menjawab seluruh pertanyaan, jelaskan dengan jujur dan sarankan untuk membaca buku lebih lanjut. 
Tetap gunakan bahasa Indonesia yang ceria dan ramah untuk anak sekolah. 
"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._call_gemini(messages)
        if response is None:
            return "Maaf, terjadi kendala teknis. Silakan coba lagi nanti ya! 🤖✨"
        return response
    
    def generate_fallback(self, user_input: str) -> str:
        """
        Generate a polite refusal or clarification if the input is out of context.
        Called by API when detecting off-topic questions (optional safety net).
        """
        return (
            "Halo hebat! 😊\n\n"
            "Saya adalah asisten khusus untuk merekomendasikan buku pelajaran dan menjawab pertanyaan seputar isi buku.\n"
            "Silakan tanyakan tentang mata pelajaran seperti matematika, IPA, bahasa Indonesia, atau minta rekomendasi buku untuk jenjang SD/SMP/SMA.\n"
            "Pertanyaan di luar itu maaf belum bisa saya bantu. Yuk fokus belajar bersama buku! 📚✨"
        )


# Optional: convenience function to instantiate with settings
def get_answer_generator() -> AnswerGenerator:
    """Factory to create AnswerGenerator using config settings."""
    from config.settings import GEMINI_API_KEY, ANSWER_MODEL
    return AnswerGenerator(model=ANSWER_MODEL)