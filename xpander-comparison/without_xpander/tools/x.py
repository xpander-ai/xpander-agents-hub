import os
import requests

api_key = os.getenv("X_API_KEY")

def search_people_twitter(api_key, screenname, rest_id=None):
    """
    Retrieves media associated with a specific Twitter user.

    Parameters:
        screenname (str): The Twitter handle of the user (e.g., 'elonmusk'). (Required)
        rest_id (str, optional): Overrides the screenname if provided. (Optional)

    Returns:
        dict: The JSON response from the Twitter API containing user media.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://twitter-api45.p.rapidapi.com/usermedia.php"
    
    querystring = {"screenname": screenname}
    if rest_id:
        querystring["rest_id"] = rest_id

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()




def list_timeline_twitter( list_id, cursor=None):
    """
    Retrieves the timeline of a specific Twitter list.

    Parameters:
        list_id (str): The unique identifier for the Twitter list. (Required)
        cursor (str, optional): Pagination cursor to fetch the next set of results. (Optional)

    Returns:
        dict: The JSON response from the Twitter API containing list timeline data.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://twitter-api45.p.rapidapi.com/listtimeline.php"
    
    querystring = {"list_id": list_id}
    if cursor:
        querystring["cursor"] = cursor

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()



def search_twitter( query, cursor=None, search_type=None):
    """
    Performs a search on Twitter based on the provided query.

    Parameters:
        query (str): The search query string (e.g., 'cybertruck'). (Required)
        cursor (str, optional): Pagination cursor to fetch the next set of results. (Optional)
        search_type (str, optional): Type of search. Available options depend on the API documentation. (Optional)

    Returns:
        dict: The JSON response from the Twitter API containing search results.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    
    querystring = {"query": query}
    if cursor:
        querystring["cursor"] = cursor
    if search_type:
        querystring["search_type"] = search_type

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()



def get_timeline_twitter( screenname, rest_id=None, cursor=None):
    """
    Retrieves the timeline of a specific Twitter user.

    Parameters:
        screenname (str): The Twitter handle of the user (e.g., 'elonmusk'). (Required)
        rest_id (str, optional): Overrides the screenname if provided. (Optional)
        cursor (str, optional): Pagination cursor to fetch the next set of results. (Optional)

    Returns:
        dict: The JSON response from the Twitter API containing user timeline data.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://twitter-api45.p.rapidapi.com/timeline.php"
    
    querystring = {"screenname": screenname}
    if rest_id:
        querystring["rest_id"] = rest_id
    if cursor:
        querystring["cursor"] = cursor

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()
