import os
from typing import Dict, Any
from tavily import TavilyClient
api_key = os.getenv("TAVILY_TOKEN")


def search(
    self,
    query: str,
    max_results: int = 5,
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_images: bool = False,
) -> Dict[str, Any]:
    """
    Perform a search query using Tavily API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        include_answer: Include AI-generated answer
        include_raw_content: Include raw HTML content
        include_images: Include related images

    Returns:
        Dict containing search results and metadata

    Raises:
        MissingAPIKeyError: If API key is missing
        InvalidAPIKeyError: If API key is invalid
        UsageLimitExceededError: If usage limit is exceeded
    """
    self.client = TavilyClient(api_key=api_key)
    try:
        response = self.client.search(
            query=query,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images
        )
        return response
    except Exception as e:
        raise e
