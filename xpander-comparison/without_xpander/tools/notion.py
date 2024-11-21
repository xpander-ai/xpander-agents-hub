import os
import requests

notion_api_key = os.getenv("NOTION_API_KEY")

def notion_search(
    query=None,
    filter_value=None,
    filter_property=None,
    sort_direction=None,
    sort_timestamp=None
):
    url = 'https://api.notion.com/v1/search'
    
    headers = {
        'Authorization': f'Bearer {notion_api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {}

    if query is not None:
        data['query'] = query

    if filter_value is not None and filter_property is not None:
        data['filter'] = {
            "value": filter_value,
            "property": filter_property
        }

    if sort_direction is not None and sort_timestamp is not None:
        data['sort'] = {
            "direction": sort_direction,
            "timestamp": sort_timestamp
        }

    response = requests.post(url, headers=headers, json=data)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def query_notion_database(
    database_id,
    filter=None,
    sorts=None,
    start_cursor=None,
    page_size=None,
    filter_properties=None
):
    """
    Queries a database and returns a list of pages and/or databases contained in the database,
    filtered and ordered according to the filter conditions and sort criteria provided.

    Parameters:
        database_id (str): The ID of the database to query.
        filter (dict, optional): Filter conditions.
        sorts (list, optional): Sort criteria.
        start_cursor (str, optional): Cursor to start pagination from.
        page_size (int, optional): Number of results per page (max 100).
        filter_properties (list, optional): List of property IDs to include in the response.

    Returns:
        dict: The query results as a JSON response.
    """
    url = f'https://api.notion.com/v1/databases/{database_id}/query'

    # Add query parameters if filter_properties are provided
    params = {}
    if filter_properties:
        params['filter_properties'] = filter_properties

    headers = {
        'Authorization': f'Bearer {notion_api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {}
    if filter is not None:
        data['filter'] = filter
    if sorts is not None:
        data['sorts'] = sorts
    if start_cursor is not None:
        data['start_cursor'] = start_cursor
    if page_size is not None:
        data['page_size'] = page_size

    response = requests.post(url, headers=headers, json=data, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()

def create_notion_page(
    parent,
    properties,
    icon=None,
    cover=None,
    children=None
):
    """
    Creates a new page in Notion.

    Parameters:
        parent (dict): The parent page or database where the new page will be created.
                       Should be a dict with either 'page_id' or 'database_id'.
        properties (dict): The properties of the new page. If the parent is a database,
                           the keys should match the database's properties.
        icon (dict, optional): The icon of the page. Can be an emoji or external file.
        cover (dict, optional): The cover image of the page.
        children (list, optional): Content blocks to be added to the page.

    Returns:
        dict: The created page object as a JSON response.
    """
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {notion_api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {
        'parent': parent,
        'properties': properties
    }

    if icon is not None:
        data['icon'] = icon
    if cover is not None:
        data['cover'] = cover
    if children is not None:
        data['children'] = children

    response = requests.post(url, headers=headers, json=data)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def append_block_children(
    block_id,
    children,
    after=None
):
    """
    Appends child blocks to a parent block.

    Parameters:
        block_id (str): The ID of the parent block or page.
        children (list): A list of block objects to append as children.
        after (str, optional): The ID of an existing block after which the new blocks will be appended.

    Returns:
        dict: The JSON response from the Notion API containing the appended blocks.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = f'https://api.notion.com/v1/blocks/{block_id}/children'
    headers = {
        'Authorization': f'Bearer {notion_api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    data = {
        'children': children
    }
    if after is not None:
        data['after'] = after

    response = requests.patch(url, headers=headers, json=data)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()
