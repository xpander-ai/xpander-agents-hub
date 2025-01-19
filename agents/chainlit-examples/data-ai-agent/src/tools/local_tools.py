import os
import json
import time
from typing import Dict, List, Any, Optional

from src.database.vector_store import vector_store
from src.utils.query_logger import query_logger

def fetch_youtube_transcript(video_url: str) -> Dict[str, Any]:
    """Fetch and process YouTube video transcript."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Extract video ID from URL
        video_id = video_url.split("v=")[-1].split("&")[0]
        
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Process transcript into text
        full_text = " ".join([entry["text"] for entry in transcript])
        
        # Generate summary using the vector store's summarization
        summary_metadata = vector_store._generate_summary(full_text, f"youtube_transcript_{video_id}")
        
        # Store in vector DB with source and metadata
        vector_store.add_text(full_text, f"youtube_transcript_{video_id}")
        
        # Also save to file for reference
        file_path = os.path.join("knowledge_repo", f"{video_id}_transcript.txt")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        # Return comprehensive response
        return {
            "success": True,
            "video_id": video_id,
            "summary": summary_metadata["summary"],
            "topics": summary_metadata["topics"],
            "content_type": summary_metadata["content_type"],
            "transcript_preview": full_text[:500] + "..." if len(full_text) > 500 else full_text,
            "full_transcript_path": file_path,
            "total_length": len(full_text),
            "note": "Full transcript has been saved to file and vector store. Use memory-search to query specific parts."
        }
    except Exception as e:
        return {"error": f"Failed to fetch transcript: {str(e)}"}

async def write_file(path: str, file_content: str, file_type: str = "text") -> Dict[str, Any]:
    """Write content to file and optionally store in vector DB."""
    try:
        # If path is just a filename, store it in the knowledge repo
        if not os.path.dirname(path):
            path = os.path.join("knowledge_repo", path)
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        # Write file
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
            
        # Store in vector DB if it's a text file
        if file_type.lower() in ["text", "markdown", "code"]:
            vector_store.add_text(file_content, f"file_{path}")
            
        return {
            "success": True,
            "path": path,
            "size": len(file_content)
        }
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}

def read_file(path: str, fmt: str = "string") -> Dict[str, Any]:
    """Read file content."""
    try:
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if fmt == "json":
            try:
                return json.loads(content)
            except:
                return {"error": "Failed to parse JSON content"}
        else:
            return {"content": content}
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}

def memory_search(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Search vector store with metadata."""
    try:
        # If the query looks like a YouTube URL, try to fetch it first
        if "youtube.com/watch?v=" in query or "youtu.be/" in query:
            transcript_result = fetch_youtube_transcript(query)
            if transcript_result.get("success"):
                return {
                    "success": True,
                    "summary": transcript_result["summary"],
                    "topics": transcript_result["topics"],
                    "content_type": transcript_result["content_type"],
                    "source": f"youtube_transcript_{transcript_result['video_id']}",
                    "note": "Transcript fetched and summarized. Use memory-search with specific queries to explore details."
                }
        
        # Regular memory search
        results = vector_store.search(query=query, top_k=top_k)
        return {
            "success": True,
            "results": results,
            "total_results": len(results)
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

def list_memories() -> Dict[str, Any]:
    """List all memories with metadata."""
    try:
        memories = vector_store.list_memories()
        return {
            "success": True,
            "memories": memories,
            "total": len(memories)
        }
    except Exception as e:
        return {"error": f"Failed to list memories: {str(e)}"}

def get_memory_stats() -> Dict[str, Any]:
    """Get statistics about the memory store."""
    try:
        stats = vector_store.get_memory_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {"error": f"Failed to get stats: {str(e)}"}

def delete_memory(memory_id: str) -> Dict[str, bool]:
    """Delete a specific memory."""
    try:
        success = vector_store.delete_memory(memory_id)
        return {"success": success}
    except Exception as e:
        return {"error": f"Failed to delete memory: {str(e)}"}

def delete_source(source: str) -> Dict[str, Any]:
    """Delete all memories from a source."""
    try:
        count = vector_store.delete_source(source)
        return {
            "success": True,
            "deleted_count": count
        }
    except Exception as e:
        return {"error": f"Failed to delete source: {str(e)}"}

def clean_duplicates() -> Dict[str, Any]:
    """Remove duplicate memories."""
    try:
        count = vector_store.clean_duplicates()
        return {
            "success": True,
            "removed_count": count
        }
    except Exception as e:
        return {"error": f"Failed to clean duplicates: {str(e)}"}

def clear_all_memories() -> Dict[str, Any]:
    """Clear all memories."""
    try:
        count = vector_store.clear_all_memories()
        return {
            "success": True,
            "cleared_count": count
        }
    except Exception as e:
        return {"error": f"Failed to clear memories: {str(e)}"}

def read_query_logs(
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Read query logs with optional time range."""
    try:
        logs = query_logger.read_logs(start_time, end_time, limit)
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        return {"error": f"Failed to read logs: {str(e)}"}

def get_query_stats(
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> Dict[str, Any]:
    """Get query statistics."""
    try:
        stats = query_logger.get_stats(start_time, end_time)
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {"error": f"Failed to get query stats: {str(e)}"}

# Export tools for agent
local_tools = [
    {
        "type": "function",
        "function": {
            "name": "fetch-youtube-transcript",
            "description": "Fetch and store transcript from a YouTube video",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": "YouTube video URL"
                    }
                },
                "required": ["video_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write-file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "fileContent": {
                        "type": "string",
                        "description": "Content to write"
                    },
                    "fileType": {
                        "type": "string",
                        "description": "Type of file (text, markdown, code, etc)",
                        "default": "text"
                    }
                },
                "required": ["path", "fileContent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read-file",
            "description": "Read file content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "fmt": {
                        "type": "string",
                        "description": "Format to return (string or json)",
                        "default": "string"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory-search",
            "description": "Search through stored memories (async)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list-memories",
            "description": "List all stored memories",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get-memory-stats",
            "description": "Get statistics about stored memories",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete-memory",
            "description": "Delete a specific memory by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of memory to delete"
                    }
                },
                "required": ["memory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete-source",
            "description": "Delete all memories from a specific source",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source identifier"
                    }
                },
                "required": ["source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clean-duplicates",
            "description": "Remove duplicate memories",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear-all-memories",
            "description": "Clear all stored memories",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read-query-logs",
            "description": "Read query logs with optional time range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "number",
                        "description": "Start timestamp (optional)"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End timestamp (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of logs to return",
                        "default": 100
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get-query-stats",
            "description": "Get query statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "number",
                        "description": "Start timestamp (optional)"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End timestamp (optional)"
                    }
                }
            }
        }
    }
] 