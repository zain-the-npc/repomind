import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")          # optional, raises rate limit
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")       # embeddings + generation
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")        # only needed for Qdrant Cloud

# Embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# LLM for answer generation
LLM_MODEL = "gpt-4o-mini"

# Chunking
MAX_CHUNK_TOKENS = 500
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c"}
DOC_EXTENSIONS = {".md", ".rst", ".txt"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", "venv", ".venv"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "poetry.lock"}
MAX_FILE_SIZE_BYTES = 200_000  # skip huge generated files

# Retrieval
HYBRID_TOP_K = 20      # candidates from hybrid search before rerank
RERANK_TOP_K = 5        # final chunks sent to LLM