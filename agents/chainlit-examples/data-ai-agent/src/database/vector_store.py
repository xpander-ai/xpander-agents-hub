import os
import json
import time
import openai
import tiktoken
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

from src.config.settings import (
    KNOWLEDGE_REPO_DIR,
    EMBED_CACHE_FILE,
    VECTOR_DB_FILE,
    PRIMARY_EMBED_MODEL,
    FALLBACK_EMBED_MODEL,
    MAX_CACHE_SIZE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MIN_SIMILARITY,
    DYNAMIC_SIMILARITY,
    MAX_RERANK_CANDIDATES,
)

class VectorStore:
    def __init__(self):
        self.embed_cache: Dict[str, List[float]] = {}
        self.vector_db: List[Dict[str, Any]] = []
        self.embedding_dim: Optional[int] = None
        self.init_store()

    def _validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding dimensions and values."""
        if not embedding or not isinstance(embedding, list):
            return False
        if self.embedding_dim and len(embedding) != self.embedding_dim:
            return False
        return all(isinstance(x, float) for x in embedding)

    def _evict_oldest_entries(self, count: int):
        """Remove oldest entries from embedding cache."""
        if len(self.embed_cache) <= count:
            return
        
        # Sort by timestamp if available, otherwise just take random entries
        sorted_entries = sorted(
            [(k, self.vector_db.get(k, {}).get('timestamp', 0)) 
             for k in self.embed_cache.keys()],
            key=lambda x: x[1]
        )
        
        for key, _ in sorted_entries[:count]:
            del self.embed_cache[key]

    def cos_sim(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity with proper validation."""
        if not self._validate_embedding(a) or not self._validate_embedding(b):
            return 0.0
        
        if len(a) != len(b):
            print(f"[ERROR] Embedding dimension mismatch: {len(a)} vs {len(b)}")
            return 0.0
            
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a < 1e-9 or norm_b < 1e-9:  # Handle near-zero vectors
            return 0.0
            
        try:
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception as e:
            print(f"[ERROR] Cosine similarity calculation failed: {e}")
            return 0.0

    def embed_text(self, text: str) -> List[float]:
        """Return an embedding for text with improved caching and validation."""
        if not text.strip():
            return []
            
        # Check cache with validation
        if text in self.embed_cache:
            cached_embedding = self.embed_cache[text]
            if self._validate_embedding(cached_embedding):
                return cached_embedding
            else:
                del self.embed_cache[text]

        # Implement cache eviction if needed
        if len(self.embed_cache) >= MAX_CACHE_SIZE:
            self._evict_oldest_entries(MAX_CACHE_SIZE // 10)  # Remove 10% oldest entries

        # Try embedding with retries
        max_retries = 3
        for attempt in range(max_retries):
            for model_name in [PRIMARY_EMBED_MODEL, FALLBACK_EMBED_MODEL]:
                try:
                    print(f"[EMBED] Attempt {attempt + 1}/{max_retries} with model={model_name}...")
                    resp = openai.embeddings.create(input=text, model=model_name)
                    embedding = resp.data[0].embedding
                    
                    # Validate and store embedding dimension
                    if self._validate_embedding(embedding):
                        if not self.embedding_dim:
                            self.embedding_dim = len(embedding)
                        self.embed_cache[text] = embedding
                        self.save_store()
                        return embedding
                except Exception as e:
                    print(f"[EMBED] Failed with {model_name} (attempt {attempt + 1}): {e}")
                    time.sleep(min(2 ** attempt, 8))  # Exponential backoff

        print("[EMBED] All embedding attempts failed")
        return []

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into overlapping chunks with position tracking."""
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
        except:
            enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

        tokens = enc.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_tokens = tokens[i:i + CHUNK_SIZE]
            chunk_text = enc.decode(chunk_tokens)
            start_pos = i
            end_pos = i + len(chunk_tokens)
            chunks.append((chunk_text, start_pos, end_pos))
            
        return chunks

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

    def _generate_summary(self, text: str, source: str) -> Dict[str, str]:
        """Generate a summary and semantic metadata for the text using GPT."""
        try:
            client = openai.OpenAI()
            
            prompt = f"""Analyze this content and provide a JSON response with these keys:
- summary: A concise summary (2-3 sentences)
- topics: Key topics/concepts (comma-separated)
- content_type: Type of content (e.g., 'API Response', 'Code', 'Documentation')

Source context: {source}

Content to analyze:
{text[:1000]}... (truncated)

Respond ONLY with a valid JSON object containing the above keys."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "You are a precise content analyzer. You must respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }]
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "summary": result["summary"],
                "topics": result["topics"],
                "content_type": result["content_type"]
            }
        except Exception as e:
            print(f"[ERROR] Summary generation failed: {e}")
            return {
                "summary": "Summary generation failed",
                "topics": "unknown",
                "content_type": "unknown"
            }

    def add_text(self, text: str, source: str):
        """Add text to vector store with improved chunking, summarization and metadata."""
        print(f"[VDB] Storing text from source='{source}', length={len(text)}.")
        
        # Check for duplicates first
        text_hash = hash(text)
        for entry in self.vector_db:
            if entry.get("text_hash") == text_hash:
                print(f"[VDB] Duplicate content detected for source={source}. Skipping.")
                return
        
        # Generate semantic summary and metadata
        semantic_metadata = self._generate_summary(text, source)
        
        # Get chunks with position information
        chunks = self.chunk_text(text)
        total_chunks = len(chunks)
        
        for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
            # Get embedding with retries
            embedding = self.embed_text(chunk_text)
            if not embedding:
                print(f"[VDB] Failed to embed chunk {i+1}/{total_chunks}. Skipping.")
                continue
                
            entry_id = f"{source}_chunk_{i}"
            
            # Enhanced metadata with summary
            self.vector_db.append({
                "id": entry_id,
                "meta": {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "start_position": start_pos,
                    "end_position": end_pos,
                    "chunk_size": len(chunk_text),
                    "summary": semantic_metadata["summary"],
                    "topics": semantic_metadata["topics"],
                    "content_type": semantic_metadata["content_type"]
                },
                "text": chunk_text,
                "text_hash": hash(chunk_text),
                "embedding": embedding,
                "timestamp": time.time()
            })
            print(f"[VDB] Saved chunk={entry_id}, chunk_length={len(chunk_text)}")
            
        try:
            self.save_store()
            print(f"[VDB] Done storing. DB now has {len(self.vector_db)} entries.")
        except Exception as e:
            print(f"[ERROR] Failed to save vector store: {e}")

    def _calculate_dynamic_threshold(self, query: str) -> float:
        """Calculate dynamic similarity threshold based on query characteristics."""
        if not DYNAMIC_SIMILARITY:
            return MIN_SIMILARITY
            
        # Adjust threshold based on query length
        query_length = len(query.split())
        if query_length <= 3:
            return MIN_SIMILARITY + 0.1  # Stricter for short queries
        elif query_length >= 10:
            return MIN_SIMILARITY - 0.1  # More lenient for long queries
            
        return MIN_SIMILARITY

    def _rerank_results(self, hits: List[Tuple[float, str, str]], query: str) -> List[Tuple[float, str, str]]:
        """Rerank search results using additional criteria."""
        if len(hits) <= 1:
            return hits
            
        reranked = []
        for score, text, id in hits[:MAX_RERANK_CANDIDATES]:
            # Find the entry
            entry = next((e for e in self.vector_db if e["id"] == id), None)
            if not entry:
                continue
                
            # Calculate additional ranking factors with safe fallbacks
            meta = entry.get("meta", {})
            chunk_index = meta.get("chunk_index", 0)
            total_chunks = meta.get("total_chunks", 1)
            timestamp = entry.get("timestamp", time.time())
            
            # Avoid division by zero
            chunk_position_penalty = 0.1 * (chunk_index / total_chunks) if total_chunks > 0 else 0
            
            # Calculate recency boost (within last 24 hours)
            time_diff = time.time() - timestamp
            recency_boost = 0.1 * max(0, 1.0 - time_diff / (24 * 3600))
            
            # Combine factors
            adjusted_score = score - chunk_position_penalty + recency_boost
            reranked.append((adjusted_score, text, id))
            
        return sorted(reranked, key=lambda x: x[0], reverse=True)

    def search(self, query: str, top_k: int = 3, min_similarity: float = None) -> List[str]:
        """
        Search for similar texts in the vector store.
        
        Args:
            query: The search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of matching texts
        """
        if not query:
            return []
            
        query_embedding = self.embed_text(query)
        if not query_embedding:
            return []
            
        results = []
        similarities = []
        
        # Calculate similarities with all entries
        for entry in self.vector_db:
            if "embedding" not in entry:
                continue
                
            similarity = self.cos_sim(query_embedding, entry["embedding"])
            if min_similarity and similarity < min_similarity:
                continue
                
            similarities.append((similarity, entry))
            
        # Sort by similarity and take top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_results = similarities[:top_k]
        
        # Extract texts
        for similarity, entry in top_results:
            if "text" in entry:
                results.append(entry["text"])
                
        return results

    def list_memories(self) -> List[Dict[str, Any]]:
        """List all memories with metadata."""
        memories = []
        for entry in self.vector_db:
            memory = {
                "id": entry["id"],
                "source": entry["meta"]["source"],
                "timestamp": entry.get("timestamp", 0),
                "text_preview": entry["text"][:100] + "..." if len(entry["text"]) > 100 else entry["text"]
            }
            memories.append(memory)
        return sorted(memories, key=lambda x: x["timestamp"], reverse=True)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store."""
        if not self.vector_db:
            return {
                "total_memories": 0,
                "total_sources": 0,
                "source_counts": {},
                "oldest_memory": None,
                "newest_memory": None
            }

        source_counts = defaultdict(int)
        timestamps = []
        
        for entry in self.vector_db:
            source = entry["meta"]["source"]
            source_counts[source] += 1
            if "timestamp" in entry:
                timestamps.append(entry["timestamp"])

        stats = {
            "total_memories": len(self.vector_db),
            "total_sources": len(source_counts),
            "source_counts": dict(source_counts),
            "oldest_memory": min(timestamps) if timestamps else None,
            "newest_memory": max(timestamps) if timestamps else None
        }
        return stats

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        initial_length = len(self.vector_db)
        self.vector_db = [entry for entry in self.vector_db if entry["id"] != memory_id]
        
        if len(self.vector_db) < initial_length:
            self.save_store()
            print(f"[VDB] Deleted memory with ID: {memory_id}")
            return True
        return False

    def delete_source(self, source: str) -> int:
        """Delete all memories from a specific source."""
        initial_length = len(self.vector_db)
        self.vector_db = [entry for entry in self.vector_db if entry["meta"]["source"] != source]
        
        deleted_count = initial_length - len(self.vector_db)
        if deleted_count > 0:
            self.save_store()
            print(f"[VDB] Deleted {deleted_count} memories from source: {source}")
        return deleted_count

    def clean_duplicates(self) -> int:
        """Remove duplicate memories based on text_hash."""
        seen_hashes = set()
        unique_entries = []
        duplicates = 0

        for entry in self.vector_db:
            text_hash = entry.get("text_hash")
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                unique_entries.append(entry)
            else:
                duplicates += 1

        if duplicates > 0:
            self.vector_db = unique_entries
            self.save_store()
            print(f"[VDB] Removed {duplicates} duplicate memories")
        return duplicates

    def clear_all_memories(self) -> int:
        """Clear all memories from the store."""
        count = len(self.vector_db)
        self.vector_db = []
        self.save_store()
        print(f"[VDB] Cleared all {count} memories")
        return count

# Initialize global vector store instance
vector_store = VectorStore() 