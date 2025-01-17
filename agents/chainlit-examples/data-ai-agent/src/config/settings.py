import os

# Directory and file paths
KNOWLEDGE_REPO_DIR = "knowledge_repo"
EMBED_CACHE_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "embedding_cache.json")
VECTOR_DB_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "vector_db.json")

# Embedding models
PRIMARY_EMBED_MODEL = "text-embedding-3-large"
FALLBACK_EMBED_MODEL = "text-embedding-ada-002"
TOKEN_THRESHOLD = 3000

# Vector store settings
MAX_CACHE_SIZE = 10000  # Maximum number of embeddings to cache
CHUNK_SIZE = 500  # Token size for each chunk
CHUNK_OVERLAP = 100  # Overlap between chunks
MIN_SIMILARITY = 0.6  # Default minimum similarity threshold
DYNAMIC_SIMILARITY = True  # Whether to use dynamic similarity thresholds
MAX_RERANK_CANDIDATES = 10  # Number of candidates to consider for reranking

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
XPANDER_API_KEY = os.environ.get("XPANDER_API_KEY", "")
XPANDER_AGENT_ID = os.environ.get("XPANDER_AGENT_ID", "")

# Constants
MAX_ITER = 5  # maximum GPT calls if it keeps calling tools 