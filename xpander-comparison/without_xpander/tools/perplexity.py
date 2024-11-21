
import os
import requests

api_key = os.getenv("PERPLEXITY_API_KEY")

def perplexity_chat_completion(
    model,
    messages,
    max_tokens=None,
    temperature=0.2,
    top_p=0.9,
    return_citations=False,
    search_domain_filter=None,
    return_images=False,
    return_related_questions=False,
    search_recency_filter=None,
    top_k=0,
    stream=False,
    presence_penalty=0,
    frequency_penalty=1
):
    """
    Sends a chat completion request to the Perplexity API and returns the response.

    Parameters:
        model (str): The name of the model to use.
        messages (list): A list of message dictionaries with 'role' and 'content'.
        max_tokens (int, optional): The maximum number of tokens to generate.
        temperature (float, optional): Sampling temperature.
        top_p (float, optional): Nucleus sampling threshold.
        return_citations (bool, optional): Whether to return citations.
        search_domain_filter (list, optional): Domains to filter search results.
        return_images (bool, optional): Whether to return images.
        return_related_questions (bool, optional): Whether to return related questions.
        search_recency_filter (str, optional): Time interval for search results ('month', 'week', 'day', 'hour').
        top_k (int, optional): Number of tokens for top-k filtering.
        stream (bool, optional): Whether to stream the response.
        presence_penalty (float, optional): Penalty for new tokens based on their presence in the text so far.
        frequency_penalty (float, optional): Penalty for new tokens based on their frequency in the text so far.

    Returns:
        dict: The JSON response from the Perplexity API.

    Raises:
        HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'top_p': top_p,
        'return_citations': return_citations,
        'return_images': return_images,
        'return_related_questions': return_related_questions,
        'top_k': top_k,
        'stream': stream,
        'presence_penalty': presence_penalty,
        'frequency_penalty': frequency_penalty
    }

    # Add optional parameters if they are provided
    if max_tokens is not None:
        data['max_tokens'] = max_tokens
    if search_domain_filter is not None:
        data['search_domain_filter'] = search_domain_filter
    if search_recency_filter is not None:
        data['search_recency_filter'] = search_recency_filter

    response = requests.post(url, headers=headers, json=data)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()

