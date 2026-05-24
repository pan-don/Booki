import json
import time
import argparse
from pathlib import Path
from typing import Optional, List, Set

from tqdm import tqdm
from google import genai
from google.genai.types import EmbedContentConfig
from google.genai.errors import APIError

from config.settings import GEMINI_API_KEY, EMBEDDING_MODEL as DEFAULT_MODEL
from utils.logger import get_logger
from utils.api_key_manager import create_gemini_key_manager

logger = get_logger(__name__)

DEFAULT_DIMENSION = 1536
DEFAULT_DELAY = 0.05
DEFAULT_MAX_RETRIES = 3
RETRY_DELAY = 1.0


class GeminiEmbedder:
    def __init__(self, key_manager=None, model: str = DEFAULT_MODEL,
                 output_dim: int = DEFAULT_DIMENSION, max_retries: int = DEFAULT_MAX_RETRIES):
        self.key_manager = key_manager or create_gemini_key_manager()
        self.model = model
        self.output_dim = output_dim
        self.max_retries = max_retries
        self._init_client()

    def _init_client(self):
        key_to_use = self.key_manager.get_current_key()
        if not key_to_use:
            raise ValueError("No Gemini API key available for embedding.")
        self.client = genai.Client(api_key=key_to_use)

    def embed_text(self, text: str, task_type: Optional[str] = None) -> Optional[List[float]]:
        """Embed teks dengan retry otomatis sesuai self.max_retries dan key rotation."""
        if not text or not text.strip():
            logger.warning("Teks kosong, skip embedding")
            return None

        # total attempts (could rotate keys multiple times)
        for attempt in range(self.max_retries * len(self.key_manager.keys)):
            try:
                config = EmbedContentConfig(
                    output_dimensionality=self.output_dim,
                    task_type=task_type if task_type else None
                )
                if task_type is None:
                    config.task_type = None
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                    config=config
                )
                if response.embeddings and len(response.embeddings) > 0:
                    return response.embeddings[0].values
                else:
                    logger.error("Tidak ada embedding dalam response")
                    return None
            except Exception as e:
                error_msg = str(e)
                key_in_use = self.key_manager.get_current_key()
                logger.warning(f"Percobaan {attempt+1} gagal (Key: {key_in_use[:5]}...): {error_msg}")
                self.key_manager.report_error(key_in_use, error_msg)
                
                # Re-init client if key rotated
                new_key = self.key_manager.get_current_key()
                if new_key != key_in_use:
                    self._init_client()
                    
                time.sleep(RETRY_DELAY * (attempt % self.max_retries + 1))
        
        logger.error(f"Gagal setelah percobaan maksimal: {text[:50]}...")
        return None

    def get_completed_ids(self, output_path: Path) -> Set[str]:
        """Membaca file output yang sudah ada, mengembalikan set ID yang sudah ter-embed."""
        completed = set()
        if output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if 'id' in data:
                            completed.add(data['id'])
                    except json.JSONDecodeError:
                        logger.warning(f"Baris tidak valid di output: {line[:100]}...")
        return completed

    def _build_enhanced_text(self, doc: dict) -> str:
        """
        Membangun teks yang menggabungkan metadata (judul, jenjang, kelas, mata pelajaran)
        dengan summary_text.
        """
        metadata = doc.get("metadata", {})
        judul = metadata.get("judul_buku", "")
        jenjang = metadata.get("jenjang", "")
        kelas = metadata.get("kelas", "")
        mapel = metadata.get("mata_pelajaran", "")
        summary = doc.get("summary_text", "")

        # Menggabungkan sesuai format yang diminta
        enhanced_text = (
            f"Judul: {judul}\nJenjang: {jenjang}\nKelas: {kelas}\n"
            f"Mata Pelajaran: {mapel}\nRingkasan: {summary}"
        )
        return enhanced_text

    def process_jsonl_resumable(self, input_path: Path, output_path: Path,
                                task_type: Optional[str] = None, delay: float = DEFAULT_DELAY):
        """Proses embedding dengan kemampuan resume (skip ID yang sudah ada)."""
        if not input_path.exists():
            logger.error(f"File input tidak ditemukan: {input_path}")
            return

        completed_ids = self.get_completed_ids(output_path)
        logger.info(f"Ditemukan {len(completed_ids)} dokumen sudah diproses sebelumnya di {output_path}")

        # Baca semua dokumen input
        all_docs = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    all_docs.append(doc)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON tidak valid di input: {line[:100]}... error: {e}")

        total_docs = len(all_docs)
        pending_docs = [doc for doc in all_docs if doc.get('id') not in completed_ids]
        logger.info(f"Total dokumen: {total_docs}, sudah diproses: {len(completed_ids)}, perlu diproses: {len(pending_docs)}")

        if not pending_docs:
            logger.info("Semua dokumen sudah diproses. Tidak ada yang perlu dilakukan.")
            return

        mode = 'a' if output_path.exists() else 'w'
        with open(output_path, mode, encoding='utf-8') as outfile:
            for doc in tqdm(pending_docs, desc="Embedding (resume)"):
                doc_id = doc.get('id')

                # ======== PERUBAHAN UTAMA ========
                # Gunakan teks yang menggabungkan metadata + ringkasan
                text = self._build_enhanced_text(doc)
                # =================================

                if not text.strip():
                    logger.warning(f"Dokumen {doc_id} menghasilkan teks kosong, skip")
                    continue

                embedding = self.embed_text(text, task_type=task_type)
                if embedding is None:
                    logger.error(f"Gagal memproses dokumen {doc_id}. Akan dilewati. Jalankan ulang untuk mencoba lagi.")
                    continue

                output_doc = doc.copy()
                output_doc["embedding"] = embedding
                output_doc["embedding_model"] = self.model
                output_doc["embedding_dimension"] = self.output_dim
                if task_type:
                    output_doc["task_type"] = task_type

                outfile.write(json.dumps(output_doc, ensure_ascii=False) + "\n")
                outfile.flush()
                time.sleep(delay)

        logger.info(f"Proses selesai. Hasil disimpan di {output_path}. Total dokumen dalam output: {len(completed_ids) + len(pending_docs)}.")
    def embed_texts(self, texts: List[str], task_type: Optional[str] = None) -> List[List[float]]:
        """Mengembed banyak teks secara serial dengan return list of vectors."""
        results = []
        for t in texts:
            vec = self.embed_text(t, task_type=task_type)
            if vec is None:
                raise ValueError("Gagal mengembed salah satu chunk.")
            results.append(vec)
            time.sleep(DEFAULT_DELAY)
        return results