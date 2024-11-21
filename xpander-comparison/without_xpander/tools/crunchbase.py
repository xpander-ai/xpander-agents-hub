import os
import requests

api_key = os.getenv("CRUNCHBASE_API_KEY")

def crunchbase_autocomplete(query):
    """
    Searches for organizations matching the query string using the Crunchbase Autocomplete API.

    Parameters:
        query (str): The search query string.

    Returns:
        dict: The JSON response from the Crunchbase API.
    """
    url = 'https://crunchbase-api.p.rapidapi.com/v1/autocomplete'
    headers = {
        'x-rapidapi-host': 'crunchbase-api.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    params = {
        'query': query
    }

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def get_crunchbase_organization(organization_identifier):
    """
    Retrieves detailed information about a specific organization using the Crunchbase API.

    Parameters:
        organization_identifier (str): The unique identifier for the organization (e.g., 'amazon').

    Returns:
        dict: The JSON response from the Crunchbase API.
    """
    url = "https://crunchbase-api.p.rapidapi.com/v1/organization"
    
    querystring = {"organization_identifier": organization_identifier}
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "crunchbase-api.p.rapidapi.com"
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()
