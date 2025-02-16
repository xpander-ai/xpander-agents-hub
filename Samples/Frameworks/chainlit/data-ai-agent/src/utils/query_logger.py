import os
import json
import time
import tiktoken
from datetime import datetime
from typing import Dict, Any, Optional

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

class QueryLogger:
    # Cost per 1M tokens in USD
    INPUT_TOKEN_COST = 2.50 / 1_000_000  # $2.50 per 1M tokens
    OUTPUT_TOKEN_COST = 10.00 / 1_000_000  # $10.00 per 1M tokens
    
    def __init__(self, log_file: str = "agent_queries.jsonl"):
        """Initialize query logger with a log file in the logs directory."""
        self.log_file = os.path.join(LOGS_DIR, log_file)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Create logs directory and log file if they don't exist."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("")  # Create empty file
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on token counts."""
        input_cost = input_tokens * self.INPUT_TOKEN_COST
        output_cost = output_tokens * self.OUTPUT_TOKEN_COST
        return input_cost + output_cost
    
    def log_query(
        self,
        query: str,
        response: str,
        latency: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log query details with token counts, latency, and cost.
        
        Args:
            query: The input query text
            response: The response text
            latency: Query processing time in seconds
            metadata: Optional additional metadata
            
        Returns:
            Dict containing the logged information
        """
        input_tokens = self._count_tokens(query)
        output_tokens = self._count_tokens(response)
        total_cost = self._calculate_cost(input_tokens, output_tokens)
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_seconds": latency,
            "cost_usd": total_cost,
            "query": query,
            "response_preview": response[:200] + "..." if len(response) > 200 else response
        }
        
        if metadata:
            log_entry["metadata"] = metadata
            
        # Append to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write to log file: {e}")
            
        return log_entry
    
    def read_logs(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Read logs with optional time filtering.
        
        Args:
            start_time: ISO format datetime string for filtering start
            end_time: ISO format datetime string for filtering end
            limit: Maximum number of logs to return
            
        Returns:
            List of log entries
        """
        logs = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        
                        # Apply time filters if specified
                        if start_time and entry["timestamp"] < start_time:
                            continue
                        if end_time and entry["timestamp"] > end_time:
                            continue
                            
                        logs.append(entry)
                        
                        if len(logs) >= limit:
                            break
        except Exception as e:
            print(f"[ERROR] Failed to read log file: {e}")
            
        return logs
    
    def get_usage_stats(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate usage statistics over a time period.
        
        Args:
            start_time: ISO format datetime string for filtering start
            end_time: ISO format datetime string for filtering end
            
        Returns:
            Dict containing usage statistics
        """
        logs = self.read_logs(start_time, end_time, limit=1_000_000)  # High limit to get all logs
        
        if not logs:
            return {
                "total_queries": 0,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "avg_latency": 0.0
            }
            
        total_cost = sum(log["cost_usd"] for log in logs)
        total_tokens = sum(log["total_tokens"] for log in logs)
        avg_latency = sum(log["latency_seconds"] for log in logs) / len(logs)
        
        return {
            "total_queries": len(logs),
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "avg_latency": avg_latency,
            "start_time": logs[0]["timestamp"],
            "end_time": logs[-1]["timestamp"]
        }

# Initialize global query logger
query_logger = QueryLogger() 