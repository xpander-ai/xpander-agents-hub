import os

# Directory and file paths
KNOWLEDGE_REPO_DIR = "knowledge_repo"
EMBED_CACHE_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "embedding_cache.json")
VECTOR_DB_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "vector_db.json")

# Embedding models
PRIMARY_EMBED_MODEL = "text-embedding-3-large"
FALLBACK_EMBED_MODEL = "text-embedding-ada-002"
TOKEN_THRESHOLD = 30000

# API Keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
XPANDER_API_KEY = os.environ.get("XPANDER_API_KEY", "")
XPANDER_AGENT_ID = os.environ.get("XPANDER_AGENT_ID", "")

# Constants
MAX_ITER = 5  # maximum GPT calls if it keeps calling tools 