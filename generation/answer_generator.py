"""
Answer Generator using Gemini API (LLM).
Generates final answers for recommendations or detailed questions.
Custom prompt ensures friendly, cheerful, and easy-to-understand responses in Indonesian.
"""

import json
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import logging

from config.settings import GEMINI_API_KEY, ANSWER_MODEL
from utils.logger import get_logger
from utils.api_key_manager import APIKeyManager

logger = get_logger(__name__)

# Clean, pruned XML System Instructions
DEFAULT_SYSTEM_PROMPT = """
<role>Asisten Pintar Rumah Literasi Tambaksogra yang sangat ramah, ceria, dan suportif untuk anak sekolah (SD, SMP, SMA).</role>
<allowed_topics>Materi pendidikan, buku pelajaran, ilmu pengetahuan, tips belajar, identitas sistem, dan statistik perpustakaan.</allowed_topics>
<rejection_rule>Jika pertanyaan di luar allowed_topics, jawab: "Maaf ya, teman! Aku dirancang khusus untuk membantu kamu mengeksplorasi buku pelajaran dan ilmu pengetahuan. Yuk, kita kembali bahas buku atau materi sekolah saja! 📚✨"</rejection_rule>
<formatting>JANGAN PERNAH menuliskan ulang daftar metadata buku menggunakan poin-poin kaku (seperti list judul, penulis, halaman). Sebutkan judul buku secara natural dan mengalir di dalam paragraf analisis naratif Anda.</formatting>
"""

# Highly auditable module-level Few-Shot examples
FEW_SHOT_EXAMPLES = [
    {"role": "user", "parts": [{"text": "Saya butuh buku matematika aljabar"}]},
    {"role": "model", "parts": [{"text": "Wah, hebat sekali semangat belajarmu, Sobat Belajar! Aljabar itu seru lho... Ini dia beberapa buku yang aku temukan yang membahas konsep-konsep aljabar dengan sangat interaktif. Ingat ya, setiap rumus itu seperti teka-teki yang menyenangkan untuk dipecahkan! 📚✨"}]}
]

class AnswerGenerator:
    """
    Generates answers using Google Gemini API.
    """
    
    def __init__(
        self,
        api_key_manager: Optional[APIKeyManager] = None,
        model: str = ANSWER_MODEL,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.8,
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
        self.cache_id = None
        
        self._initialize_context_cache()
        logger.info(f"AnswerGenerator initialized with model {model}")
        
    def _initialize_context_cache(self):
        """Registers system instructions and few-shots to the Gemini server cache."""
        try:
            client = genai.Client(api_key=self.api_key_manager.get_current_key())
            # Prepare the immutable foundation content block
            cache_contents = [{"role": "system", "parts": [{"text": self.system_prompt}]}] + FEW_SHOT_EXAMPLES
            
            # Create Context Cache on server side
            cache = client.caches.create(
                model=self.model,
                config=types.CreateCacheConfig(
                    contents=cache_contents,
                    ttl="3600s" # 1 Hour lifecycle duration
                )
            )
            self.cache_id = cache.name
            logger.info(f"Gemini Context Cache successfully initialized: {self.cache_id}")
        except Exception as e:
            logger.error(f"Failed to create context cache, will default to non-cached calls: {str(e)}")
            self.cache_id = None

    def _call_gemini(self, dynamic_contents: List[Dict[str, Any]]) -> Optional[str]:
        """Executes content generation with native parameter configuration and dynamic cache fallbacks."""
        try:
            client = genai.Client(api_key=self.api_key_manager.get_current_key())
            
            # Use cached path if available
            if self.cache_id:
                try:
                    config = types.GenerateContentConfig(
                        cached_content=self.cache_id,
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens
                    )
                    response = client.models.generate_content(
                        model=self.model,
                        contents=dynamic_contents,
                        config=config
                    )
                    return response.text.strip() if response.text else None
                except Exception as cache_err:
                    logger.warning(f"Cache {self.cache_id} failed or expired, falling back to non-cached call. Err: {cache_err}")
                    self.cache_id = None  # Reset cache ID to avoid further failures

            # Fallback path / non-cached path
            config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )

            # Manually inject few-shots if not using cache
            full_contents = FEW_SHOT_EXAMPLES + dynamic_contents

            response = client.models.generate_content(
                model=self.model,
                contents=full_contents,
                config=config
            )

            return response.text.strip() if response.text else None

        except Exception as e:
            logger.error(f"Gemini API execution error: {e}")
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

Berdasarkan data di atas, bangun perbincangan naratif yang elok, ramah, analitis, dan ceria dengan panjang sekitar 3-4 paragraf yang menarik.
Sertakan alasan yang logis mengapa buku-buku ini relevan untuk pengguna.
Pada bagian akhir respons Anda, berikan 1-3 tips belajar yang sangat interaktif dan spesifik terkait subjek buku yang disebutkan.
DO NOT write rigid structural lists, bullet points, or repetitive metadata blocks for the books.
The UI will render the structured list natively. Your job is ONLY to provide the conversational, engaging chat text.
Gunakan bahasa Indonesia yang santai, selipkan emoji yang relevan seperti 📚, ✨, 😊.
"""
        
        messages = [
            {"role": "user", "parts": [{"text": user_prompt}]}
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

Jawablah pertanyaan pengguna dengan detail, jelas, dan mudah dipahami, susun menjadi 3-4 paragraf naratif yang elok.
Sebutkan dari buku mana informasi itu berasal (dan halaman jika ada). 
Pada bagian akhir respons Anda, sertakan 1-3 tips belajar yang spesifik dan interaktif mengenai topik yang dibahas.
Jika informasi tidak cukup untuk menjawab seluruh pertanyaan, jelaskan dengan jujur dan sarankan untuk membaca buku lebih lanjut. 
DO NOT write rigid structural lists, bullet points, or repetitive metadata blocks for the books.
Tetap gunakan bahasa Indonesia yang ceria dan ramah untuk anak sekolah. 
"""
        
        messages = [
            {"role": "user", "parts": [{"text": user_prompt}]}
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