import os
import requests

api_key = os.getenv("LINKEDIN_API_KEY")

def search_people_linkedin(keywords=None, start=0, geo=None, 
                          schoolId=None, firstName=None, lastName=None, 
                          keywordSchool=None, keywordTitle=None, company=None):
    """
    Searches for people on LinkedIn based on various criteria.

    Parameters:
        keywords (str, optional): Keywords to search for (e.g., 'max').
        start (str, optional): Pagination start point (e.g., '0', '10', '20').
        geo (str, optional): Geographical location IDs separated by commas (e.g., '103644278,101165590').
        schoolId (str, optional): Identifier for the school.
        firstName (str, optional): First name of the person.
        lastName (str, optional): Last name of the person.
        keywordSchool (str, optional): Keywords related to the school.
        keywordTitle (str, optional): Keywords related to the job title.
        company (str, optional): Company name.

    Returns:
        dict: The JSON response from the LinkedIn Data API containing search results.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://linkedin-data-api.p.rapidapi.com/search-people"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    params = {}
    if keywords:
        params['keywords'] = keywords
    if start:
        params['start'] = start
    if geo:
        params['geo'] = geo
    if schoolId:
        params['schoolId'] = schoolId
    if firstName:
        params['firstName'] = firstName
    if lastName:
        params['lastName'] = lastName
    if keywordSchool:
        params['keywordSchool'] = keywordSchool
    if keywordTitle:
        params['keywordTitle'] = keywordTitle
    if company:
        params['company'] = company

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def search_employees_linkedin(companyId, start=0, geoIds=None, 
                              seniorityLevels=None, currentTitles=None):
    """
    Searches for employees of a specific company on LinkedIn based on various criteria.

    Parameters:
        companyId (str): The unique identifier for the company (e.g., '1441').
        start (str, optional): Pagination start point (e.g., '0', '50', '100').
        geoIds (str, optional): Geographical location IDs separated by commas (e.g., '90009735,103035651').
        seniorityLevels (str, optional): Seniority levels separated by commas (e.g., 'manager,senior').
        currentTitles (str, optional): Current job titles separated by commas (e.g., 'Engineer,Developer').

    Returns:
        dict: The JSON response from the LinkedIn Data API containing search results.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://linkedin-data-api.p.rapidapi.com/search-employees"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    params = {
        'companyId': companyId,
        'start': start
    }
    if geoIds:
        params['geoIds'] = geoIds
    if seniorityLevels:
        params['seniorityLevels'] = seniorityLevels
    if currentTitles:
        params['currentTitles'] = currentTitles

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def get_company_by_domain_linkedin(domain):
    """
    Retrieves detailed information about a company using its domain name via the LinkedIn Data API.

    Parameters:
        domain (str): The domain name of the company (e.g., 'apple.com').

    Returns:
        dict: The JSON response from the LinkedIn Data API containing company details.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://linkedin-data-api.p.rapidapi.com/get-company-by-domain"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    params = {
        'domain': domain
    }

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()


def get_company_posts_linkedin( username, start=0, paginationToken=None):
    """
    Retrieves posts made by a specific company on LinkedIn.

    Parameters:
        username (str): The LinkedIn username of the company (e.g., 'microsoft').
        start (str, optional): Pagination start point (e.g., '0', '50', '100').
        paginationToken (str, optional): Token for fetching the next page of results.

    Returns:
        dict: The JSON response from the LinkedIn Data API containing company posts.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    url = "https://linkedin-data-api.p.rapidapi.com/get-company-posts"
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    params = {
        'username': username,
        'start': start
    }
    if paginationToken:
        params['paginationToken'] = paginationToken

    response = requests.get(url, headers=headers, params=params)
    try:
        response.raise_for_status()
    except Exception:
        raise Exception(response.content)
    return response.json()
