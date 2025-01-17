import os
import json
import csv
from io import StringIO
import xml.etree.ElementTree as ET
from typing import Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi

from src.config.settings import KNOWLEDGE_REPO_DIR, TOKEN_THRESHOLD
from src.database.vector_store import vector_store

def fetch_youtube_transcript(video_url: str) -> Dict[str, str]:
    """Fetch a YouTube transcript."""
    print(f"[TOOL] fetch_youtube_transcript => {video_url}")
    try:
        # Extract video ID consistently
        if "watch?v=" in video_url:
            vid = video_url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in video_url:
            vid = video_url.split("/")[-1]
        else:
            return {"error": "Invalid URL pattern."}

        data = YouTubeTranscriptApi.get_transcript(vid)
        text = " ".join(e["text"] for e in data)
        
        print(f"[TRANSCRIPT] Got transcript of length: {len(text)}")
        
        # Use consistent source ID format
        source_id = f"youtube_{vid}"
        print(f"[TRANSCRIPT] Saving to vector store with source: {source_id}")
        
        try:
            vector_store.add_text(text, source_id)
            db_size = len(vector_store.vector_db)
            print(f"[TRANSCRIPT] Successfully saved to vector store (DB size: {db_size})")
            
            return {
                "transcript": text,
                "info": f"Transcript saved to vector store (DB size: {db_size})"
            }
        except Exception as e:
            print(f"[ERROR] Failed to save to vector store: {str(e)}")
            return {
                "transcript": text,
                "warning": "Transcript retrieved but failed to save to vector store"
            }
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch transcript: {str(e)}")
        return {"error": str(e)}

def read_file(path: str, fmt: str = "string") -> Dict[str, Any]:
    """Read and format file contents."""
    print(f"[TOOL] read_file => {path}, fmt={fmt}")
    if not os.path.exists(path):
        path = os.path.join(KNOWLEDGE_REPO_DIR, path)
    if not os.path.exists(path):
        return {"error": "File not found."}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except:
        return {"error": "Couldn't read file."}

    if len(content) > 10000:
        snippet = content[:1000]
        return {
            "info": "File large. Partial only. Use vector search for more detail.",
            "content": snippet
        }

    if fmt == "json":
        try:
            return {"content": json.loads(content)}
        except:
            return {"error": "Invalid JSON."}
    elif fmt == "csv":
        return {"content": list(csv.reader(StringIO(content)))}
    elif fmt == "xml":
        try:
            root = ET.fromstring(content)
            return {"content": ET.tostring(root, encoding="unicode")}
        except:
            return {"error": "Invalid XML."}
    else:
        return {"content": content}

def write_file(path: str, file_content: str, file_type: str) -> Dict[str, str]:
    """Write content to file with proper formatting."""
    print(f"[TOOL] write_file => {path}, fileType={file_type}")
    if not path.startswith(KNOWLEDGE_REPO_DIR):
        path = os.path.join(KNOWLEDGE_REPO_DIR, path)
    try:
        if file_type.lower() == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(json.loads(file_content), f, indent=2)
        elif file_type.lower() == "xml":
            root = ET.Element("root")
            ET.SubElement(root, "content").text = file_content
            ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=True)
        elif file_type.lower() == "csv":
            rows = list(csv.reader(StringIO(file_content)))
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(file_content)

        vector_store.add_text(file_content, os.path.basename(path))
        return {"success": f"Wrote file: {path}"}
    except Exception as e:
        return {"error": str(e)}

def memory_search(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Search agent's memory (vector store) for relevant content."""
    print(f"[MEMORY] Original query: {query[:100]}...")
    
    # Convert specific types of queries into semantic search queries
    search_query = query
    if "youtube.com/watch?v=" in query or "youtu.be/" in query:
        search_query = "video content and summary"
        print(f"[MEMORY] URL detected, converting to semantic search: {search_query}")
    elif query.startswith("http"):
        search_query = "content and summary from the webpage"
        print(f"[MEMORY] URL detected, converting to semantic search: {search_query}")
    
    print(f"[MEMORY] Vector DB size: {len(vector_store.vector_db)}")
    print("[MEMORY] Available memories:")
    for entry in vector_store.vector_db:
        print(f"  - ID: {entry['id']}, Content preview: {entry['text'][:100]}...")
    
    chunks = vector_store.search(search_query, top_k=top_k, min_similarity=0.3)  # Low threshold for better recall
    
    if not chunks:
        print("[MEMORY] No relevant memories found")
        return {
            "chunks": [],
            "info": "No relevant information found in memory."
        }
    
    print(f"[MEMORY] Found {len(chunks)} relevant memories")
    # Extract just the content from the formatted chunks
    clean_chunks = []
    for chunk in chunks:
        # Remove the [id] prefix if present
        if '] ' in chunk:
            clean_chunks.append(chunk.split('] ', 1)[1])
        else:
            clean_chunks.append(chunk)
            
    return {
        "chunks": clean_chunks,
        "info": f"Found {len(chunks)} relevant pieces of information in memory."
    }

# Tool definitions for the agent
local_tools = [
    {
        "type": "function",
        "function": {
            "name": "fetch-youtube-transcript",
            "description": "Fetch a YouTube transcript.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {"type": "string"}
                },
                "required": ["video_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory-search",
            "description": "Search agent's long-term memory for relevant information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "number"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read-file",
            "description": "Reads local file. Partial if huge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "fmt": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write-file",
            "description": "Writes local file & stores in DB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "fileContent": {"type": "string"},
                    "fileType": {"type": "string"}
                },
                "required": ["path", "fileContent", "fileType"]
            }
        }
    }
] 