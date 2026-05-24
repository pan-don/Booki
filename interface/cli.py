import sys
from pathlib import Path
from typing import List

# Tambahkan root proyek ke path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH
from utils.logger import configure_root_logger, get_logger
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from embedding.embedder import GeminiEmbedder
from retrieval.retriever import Retriever
from retrieval.reranker import Reranker
from generation.answer_generator import AnswerGenerator
from utils.file_utils import read_jsonl
from utils.api_key_manager import create_gemini_key_manager

# Import evaluators
from evaluation.precision_k import PrecisionKEvaluator
from evaluation.ragas import RagasEvaluator

# Konfigurasi logger
configure_root_logger(log_file=Path("logs/cli.log"), level=20)
logger = get_logger(__name__)


class RAGCLI:
    def __init__(self):
        logger.info("Initializing RAG components...")
        
        # Inisialisasi API key manager (rolling keys)
        self.key_manager = None
        try:
            self.key_manager = create_gemini_key_manager()
            key_count = len(self.key_manager.keys) if hasattr(self.key_manager, 'keys') else "?"
            logger.info(f"API Key Manager initialized with {key_count} keys")
        except Exception as e:
            logger.warning(f"Could not initialize APIKeyManager: {e}. Running without rolling keys.")
        
        # Embedder dengan rolling key jika tersedia
        self.embedder = GeminiEmbedder(key_manager=self.key_manager)
        
        # Dapatkan dimensi embedding
        dummy_vec = self.embedder.embed_text("test")
        dim = len(dummy_vec) if dummy_vec else 768
        
        self.summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dim)
        self.fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dim)
        self.retriever = Retriever(self.summary_store, self.fulltext_store)
        self.reranker = Reranker()
        self.answer_gen = AnswerGenerator()

        # Metadata buku
        self.book_metadata = self._load_metadata()
        logger.info("CLI ready")

    def _load_metadata(self):
        metadata = {}
        path = Path("data/metadata/content_books.jsonl")
        if path.exists():
            for item in read_jsonl(path):
                if "book_id" in item:
                    metadata[item["book_id"]] = item
            logger.info(f"Loaded {len(metadata)} book metadata")
        else:
            logger.warning("Metadata file not found")
        return metadata

    def recommend(self, query: str):
        print(f"\n🔍 Mencari rekomendasi: {query}")
        vec = self.embedder.embed_text(query)
        if not vec:
            print("❌ Embedding gagal")
            return
        results = self.retriever.search_summary(vec, top_k=20)
        if not results:
            print("📭 Tidak ada hasil")
            return
        reranked = self.reranker.rerank_results(query, results, "summary_text", top_n=5)
        answer = self.answer_gen.generate_recommendation(query, reranked)
        print("\n" + "=" * 60)
        print("📚 REKOMENDASI")
        print("=" * 60)
        print(answer)
        print("\n📖 Detail:")
        for i, b in enumerate(reranked[:3], 1):
            title = b.get("title", "?")
            score = b.get("rerank_score", 0)
            print(f"{i}. {title} (skor: {score:.3f})")
        print("=" * 60)

    def deep_dive(self, book_ids: List[str], question: str):
        if not 1 <= len(book_ids) <= 5:
            print("❌ Pilih 1-5 book_id")
            return
        print(f"\n🔍 Pertanyaan: {question}")
        print(f"📚 Buku: {', '.join(book_ids)}")
        vec = self.embedder.embed_text(question)
        if not vec:
            print("❌ Embedding gagal")
            return
        chunks = self.retriever.search_fulltext_by_book_ids(vec, book_ids, top_k=20)
        if not chunks:
            print("📭 Tidak ada potongan relevan")
            return
        reranked = self.reranker.rerank_results(question, chunks, "chunk_text", top_n=5)
        selected = [self.book_metadata.get(bid, {"book_id": bid, "title": bid}) for bid in book_ids]
        answer = self.answer_gen.generate_deep_answer(question, selected, reranked)
        print("\n" + "=" * 60)
        print("📖 JAWABAN DETAIL")
        print("=" * 60)
        print(answer)
        print("\n📌 Sumber:")
        for i, c in enumerate(reranked[:3], 1):
            title = c.get("title", "?")
            page = c.get("page", "?")
            print(f"{i}. {title} (halaman {page})")
        print("=" * 60)

    def menu(self):
        while True:
            print("\n" + "=" * 50)
            print("📘 RAG BOOK RECOMMENDER - CLI")
            print("=" * 50)
            print("1. Rekomendasi buku")
            print("2. Pendalaman (pilih buku + tanya)")
            print("3. Evaluasi precision@k")
            print("4. Evaluasi RAGAS")
            print("5. Keluar")
            choice = input("Pilihan (1-5): ").strip()
            if choice == "1":
                q = input("Preferensi buku: ").strip()
                if q:
                    self.recommend(q)
            elif choice == "2":
                ids_input = input("Book ID (pisahkan koma, max 5): ").strip()
                if not ids_input:
                    continue
                ids = [x.strip() for x in ids_input.split(",") if x.strip()]
                if not 1 <= len(ids) <= 5:
                    print("Jumlah book_id harus 1-5")
                    continue
                q = input("Pertanyaan detail: ").strip()
                if q:
                    self.deep_dive(ids, q)
            elif choice == "3":
                path = input("Path file ground truth (default: data/ground_truth/precision_queries.jsonl): ").strip()
                if not path:
                    path = "data/ground_truth/precision_queries.jsonl"
                
                if not Path(path).exists():
                    print("Ground truth belum ada. Jalankan `python scripts/generate_ground_truth.py` terlebih dahulu.")
                    continue
                
                k_str = input("Nilai k (default 5): ").strip()
                k = int(k_str) if k_str.isdigit() else 5
                evaluator = PrecisionKEvaluator(
                    self.retriever, 
                    self.reranker, 
                    self.embedder,
                    key_manager=self.key_manager
                )
                try:
                    result = evaluator.evaluate(Path(path), k=k)
                    evaluator.print_report(result)
                except Exception as e:
                    print(f"❌ Error: {e}")
            elif choice == "4":
                path = input("Path file ground truth RAGAS (default: data/ground_truth/ragas_data.jsonl): ").strip()
                if not path:
                    path = "data/ground_truth/ragas_data.jsonl"
                
                if not Path(path).exists():
                    print("Ground truth belum ada. Jalankan `python scripts/generate_ground_truth.py` terlebih dahulu.")
                    continue
                    
                try:
                    evaluator = RagasEvaluator(key_manager=self.key_manager)
                    result = evaluator.evaluate(Path(path))
                    evaluator.print_report(result)
                except ImportError:
                    print("❌ Library RAGAS tidak terinstall. Jalankan: pip install ragas datasets")
                except Exception as e:
                    print(f"❌ Error: {e}")
            elif choice == "5":
                print("Sampai jumpa! 📚✨")
                break
            else:
                print("Pilihan tidak valid")


def main():
    cli = RAGCLI()
    cli.menu()


if __name__ == "__main__":
    main()