import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# GEMINI CONFIG
ALLOCATION_EMBEDDING_INDICES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
ALLOCATION_QA_INDICES = [11, 12, 13, 14, 15, 16, 17]

def _load_gemini_keys(indices):
    keys = []
    for idx in indices:
        key = os.getenv(f"GEMINI_API_KEY_{idx}")
        if key:
            clean_key = key.strip()
            if clean_key:
                keys.append(clean_key)
    return keys

GEMINI_EMBEDDING_KEYS = _load_gemini_keys(ALLOCATION_EMBEDDING_INDICES)
GEMINI_QA_KEYS = _load_gemini_keys(ALLOCATION_QA_INDICES)

# Fallback for deprecated usages expecting GEMINI_API_KEY
GEMINI_API_KEY = GEMINI_EMBEDDING_KEYS + GEMINI_QA_KEYS

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIM = 3072
ANSWER_MODEL = "gemini-2.5-pro"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/qwen-3-7b")

# JINA CONFIG
JINA_API_KEY = os.getenv("JINA_API_KEY")
JINA_RERANK_MODEL = os.getenv("JINA_RERANK_MODEL", "jina-reranker-v3")
JINA_API_URL = os.getenv("JINA_API_URL", "https://api.jina.ai/v1/rerank")

# CHUNKING CONFIG
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 2048))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 250))
MIN_PARAGRAPH_LEN = int(os.getenv("MIN_PARAGRAPH_LEN", 30))
MIN_CHUNK_LEN = int(os.getenv("MIN_CHUNK_LEN", 500))

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# PATHS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
METADATA_FILE = DATA_DIR / "metadata" / "books.json"
FAISS_DIR = DATA_DIR / "faiss"
SUMMARY_INDEX_PATH = FAISS_DIR / "rec_index.faiss"
FULLTEXT_INDEX_PATH = FAISS_DIR / "chunks_index.faiss"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "metadata").mkdir(parents=True, exist_ok=True)