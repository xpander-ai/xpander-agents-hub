import os
import json
import time
import openai
import tiktoken
import numpy as np
from typing import Dict, List, Any

from src.config.settings import (
    KNOWLEDGE_REPO_DIR,
    EMBED_CACHE_FILE,
    VECTOR_DB_FILE,
    PRIMARY_EMBED_MODEL,
    FALLBACK_EMBED_MODEL,
)

class VectorStore:
    def __init__(self):
        self.embed_cache: Dict[str, List[float]] = {}
        self.vector_db: List[Dict[str, Any]] = []
        self.init_store()

    def init_store(self):
        """Load or init knowledge_repo. Then read EMBED_CACHE & VECTOR_DB."""
        try:
            # Ensure parent directories exist
            os.makedirs(KNOWLEDGE_REPO_DIR, exist_ok=True)
            os.makedirs(os.path.dirname(EMBED_CACHE_FILE), exist_ok=True)
            os.makedirs(os.path.dirname(VECTOR_DB_FILE), exist_ok=True)
            
            self.embed_cache = self.load_json(EMBED_CACHE_FILE, {})
            self.vector_db = self.load_json(VECTOR_DB_FILE, [])
            print(f"[INIT] EMBED_CACHE size: {len(self.embed_cache)} | VECTOR_DB entries: {len(self.vector_db)}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize vector store: {e}")
            self.embed_cache = {}
            self.vector_db = []

    def load_json(self, path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed loading {path}: {e}")
            return default

    def save_json(self, path: str, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed saving {path}: {e}")

    def save_store(self):
        """Save EMBED_CACHE & VECTOR_DB to disk."""
        self.save_json(EMBED_CACHE_FILE, self.embed_cache)
        self.save_json(VECTOR_DB_FILE, self.vector_db)

    def embed_text(self, text: str) -> List[float]:
        """Return an embedding for `text`, caching results."""
        if text in self.embed_cache:
            return self.embed_cache[text]

        for model_name in [PRIMARY_EMBED_MODEL, FALLBACK_EMBED_MODEL]:
            try:
                print(f"[EMBED] Attempting model={model_name}...")
                resp = openai.embeddings.create(input=text, model=model_name)
                e = resp.data[0].embedding
                self.embed_cache[text] = e
                self.save_store()
                print("[EMBED] Success. Cached.")
                return e
            except Exception as e:
                print(f"[EMBED] Failed with {model_name}: {e}")
                time.sleep(1)

        self.embed_cache[text] = []
        self.save_store()
        print("[EMBED] All attempts failed. Returning empty embedding.")
        return []

    def add_text(self, text: str, source: str):
        """Split `text` into ~500-token chunks, embed each, store in `VECTOR_DB`."""
        print(f"[VDB] Storing text from source='{source}', length={len(text)}.")
        
        # Check for duplicates first
        text_hash = hash(text)
        for entry in self.vector_db:
            if entry.get("text_hash") == text_hash:
                print(f"[VDB] Duplicate content detected for source={source}. Skipping.")
                return
            
        chunk_size = 500
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
        except:
            enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

        tokens = enc.encode(text)
        for i in range(0, len(tokens), chunk_size):
            chunk = enc.decode(tokens[i : i+chunk_size])
            embedding = self.embed_text(chunk)
            entry_id = f"{source}_chunk_{i//chunk_size}"
            
            # Add hash for deduplication
            self.vector_db.append({
                "id": entry_id,
                "meta": {"source": source},
                "text": chunk,
                "text_hash": hash(chunk),
                "embedding": embedding
            })
            print(f"[VDB] Saved chunk={entry_id}, chunk_length={len(chunk)}")

        try:
            self.save_store()
            print(f"[VDB] Done storing. DB now has {len(self.vector_db)} entries.")
        except Exception as e:
            print(f"[ERROR] Failed to save vector store: {e}")

    def search(self, query: str, top_k: int = 3, min_similarity: float = 0.7) -> List[str]:
        """Return top_k matching chunks from DB as short strings that meet minimum similarity threshold."""
        if not self.vector_db:
            print("[VDB] DB empty.")
            return []
        q_emb = self.embed_text(query)
        if not q_emb:
            print("[VDB] empty embedding for query.")
            return []

        def cos_sim(a, b):
            denom = (np.linalg.norm(a) * np.linalg.norm(b))
            return float(np.dot(a, b) / denom) if denom else 0.0

        scored = []
        for entry in self.vector_db:
            emb = entry.get("embedding", [])
            if emb:
                s = cos_sim(q_emb, emb)
                if s >= min_similarity:  # Only include results above threshold
                    scored.append((s, entry["text"], entry["id"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        hits = scored[:top_k]
        if hits:
            print("[VDB] top hits:")
            for i,(score,chunk,cid) in enumerate(hits):
                snippet = chunk[:60] + "..." if len(chunk)>60 else chunk
                print(f" {i+1}) ID={cid}, Score={score:.4f}, chunk={snippet}")
        return [f"[{r[2]}] {r[1]}" for r in hits]

# Initialize global vector store instance
vector_store = VectorStore() 