import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# GEMINI CONFIG
GEMINI_API_KEY = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
    os.getenv("GEMINI_API_KEY_8"),
    os.getenv("GEMINI_API_KEY_9"),
    os.getenv("GEMINI_API_KEY_10"),
    os.getenv("GEMINI_API_KEY_11"),
    os.getenv("GEMINI_API_KEY_12"),
    os.getenv("GEMINI_API_KEY_13"),
    os.getenv("GEMINI_API_KEY_14"),
    os.getenv("GEMINI_API_KEY_15"),
    os.getenv("GEMINI_API_KEY_16"),
    os.getenv("GEMINI_API_KEY_17")
]

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
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 30000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 1000))
MIN_PARAGRAPH_LEN = int(os.getenv("MIN_PARAGRAPH_LEN", 30))
MIN_CHUNK_LEN = int(os.getenv("MIN_CHUNK_LEN", 1000))

# PATHS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
METADATA_FILE = DATA_DIR / "metadata" / "books.json"
FAISS_DIR = DATA_DIR / "faiss"
SUMMARY_INDEX_PATH = FAISS_DIR / "summary_index.faiss"
FULLTEXT_INDEX_PATH = FAISS_DIR / "fulltext_index.faiss"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "metadata").mkdir(parents=True, exist_ok=True)