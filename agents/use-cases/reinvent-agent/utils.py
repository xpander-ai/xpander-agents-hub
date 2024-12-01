
import time
import sys
from pathlib import Path
import qrcode
import base64
from io import BytesIO
import yaml
from email.mime.text import MIMEText
from loguru import logger
import requests
from xpander_sdk import XpanderClient
import time
import sys
from pathlib import Path
import qrcode
import base64
from io import BytesIO
import yaml

sys.path.append(str(Path(__file__).parent.parent.parent))

from agents_util.utils.generic import *
from prompts import *
from utils import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


OUTPUT_PATH = Path(__file__).parent / "collaboration_file.html"
TEMPLATE_PATH = Path(__file__).parent / 'reInvent_template.html'

def split_companies_information(retrieval_tool_results, company):
    xpander_ai_info = ""
    company_info = ""
    for tool_name, tool_result in retrieval_tool_results.items():
        tool_result_str = yaml.dump(tool_result, indent=2)
        if "notion" in tool_name.lower():
            xpander_ai_info = tool_result_str
        else:
            company_info += f"{tool_name} information about the company {company}:\n{tool_result_str}\n"
    logo_url = retrieval_tool_results.get('LinkedInCompanyManagementGetCompanyInfoByDomain', {}).get('data', {}).get('Images', {}).get('logo')
    if not logo_url:
        logo_url = retrieval_tool_results.get('tavily-insights-fetchInsightsFromTavilyAI', {}).get('images', [None])[0]
    if not logo_url:
        logo_url = "https://media.licdn.com/dms/image/v2/D4D0BAQGbFHswKC5nMQ/company-logo_200_200/company-logo_200_200/0/1726749238011/xpander_ai_logo?e=1741219200&v=beta&t=2Ts-xwumM_J9VSBDUEMjVScg5sRcj5giphLCdIfJGGQ"
    return xpander_ai_info, company_info, logo_url

def split_text_to_rows(text: str, max_length=100) -> str:
    """
    Splits HTML text into rows while preserving HTML tags and maintaining link integrity.
    Maximum characters per row is 100, excluding HTML tags from the count.
    
    Args:
        text (str): The input HTML text to split
        
    Returns:
        str: Text split into rows with <br> tags
    """
    import re

    # Remove existing newlines and normalize spaces
    text = text.replace("\n", " ").replace("  ", " ").strip().replace("<br> ", "<br>").replace(" :", ":")
    
    # Function to extract visible text from HTML
    def get_visible_text(html_text):
        # Pattern to match HTML tags
        tag_pattern = r'<[^>]+>'
        return re.sub(tag_pattern, '', html_text)

    # Function to check if a string contains an opening tag without a closing tag
    def has_unclosed_tag(text):
        return bool(re.search(r'<[^>]*$', text))

    result = []
    current_row = []
    char_count = 0
    buffer = ""
    
    # Split by spaces but preserve HTML tags
    tokens = re.findall(r'<[^>]+>|[^<>\s]+', text)
    
    for token in tokens:
        if token.startswith('<') and token.endswith('>'):
            # Handle HTML tags
            if '<br' in token:
                # Add current row if not empty
                if current_row:
                    result.append(' '.join(current_row))
                    current_row = []
                    char_count = 0
            buffer += token
        else:
            # Regular word
            if buffer:
                token = buffer + token
                buffer = ""
            
            # Calculate the length of visible text that would be added
            visible_length = len(get_visible_text(token))
            if current_row:  # Add space character if not first word
                visible_length += 1
            
            # Check if adding this token would exceed the limit
            if char_count + visible_length > max_length:
                # Don't split if we're in the middle of a link
                if not has_unclosed_tag(' '.join(current_row)):
                    result.append(' '.join(current_row))
                    current_row = []
                    char_count = visible_length
                    current_row.append(token)
                else:
                    # If in middle of link, keep adding to current row
                    current_row.append(token)
                    char_count += visible_length
            else:
                current_row.append(token)
                char_count += visible_length
    
    # Add remaining text
    if current_row:
        result.append(' '.join(current_row))
    final_result = '<br>'.join(result)
    final_result = final_result.replace('<br><br>', '<br>')
    final_result = final_result.replace('<br></li>', '<br><br></li>')
    final_result = final_result.replace('</li>', '<br><br></li>')
    final_result = final_result.replace('<br><br>', '<br>')
    final_result = final_result.replace('</li>', '<br><br></li>')
    final_result = re.sub(r'(<br>){3,}</li>', '<br><br></li>', final_result)
    return final_result

def extract_html_content(text: str) -> str:
    """
    Extracts content between ```html and ``` markers from a text string.
    
    Args:
        text (str): The input text containing HTML content between markers
        
    Returns:
        str: The extracted HTML content, or empty string if no match found
    """
    import re
    
    pattern = r"```html\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1)
    return ""

def replace_br_with_space_in_strong_tags(text: str) -> str:
    """
    Replaces <br> tags with a space if they exist between <strong> and </strong> tags.

    Args:
        text (str): The input HTML text

    Returns:
        str: Modified text with <br> replaced by space within <strong> tags
    """
    import re

    # Define a function to replace <br> with space within <strong> tags
    def replace_br(match):
        content = match.group(1)
        return f"<strong>{content.replace('<br>', ' ')}</strong>"

    # Use regex to find <strong>...</strong> and apply the replacement function
    pattern = r"<strong>(.*?)</strong>"
    modified_text = re.sub(pattern, replace_br, text, flags=re.DOTALL)

    return modified_text

def create_html_by_template(xpander_email, company_name, client_name, agent_for_company, xpander_use_cases, logo_url):
    """
    Loads and modifies the HTML template with provided parameters.
    
    Args:
        xpander_email (str): Xpander employee email
        company_name (str): Name of the company
        client_name (str): Name of the client
        agent_for_company (str): Agent information for the company
        xpander_use_cases (str): Xpander use cases information
        logo_url (str): URL of the company logo
        
    Returns:
        str: Modified HTML content
    """
    base64_logo = ""
    if logo_url:
        try:
            response = requests.get(logo_url)
            if response.status_code == 200:
                import base64
                base64_logo = f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"
        except Exception as e:
            logger.error(f"Error converting logo to base64: {str(e)}")
            
    now_date = time.strftime("%d/%m/%y")
    agent_for_company = agent_for_company.replace("\n", "")
    agent_for_company = split_text_to_rows(agent_for_company, max_length=100)
    agent_for_company = add_color_to_links(agent_for_company)
    xpander_use_cases = extract_html_content(xpander_use_cases)
    xpander_use_cases = xpander_use_cases.replace("\n", "")
    xpander_use_cases = split_text_to_rows(xpander_use_cases, max_length=100)
    xpander_use_cases = replace_br_with_space_in_strong_tags(text=xpander_use_cases)
    xpander_use_cases = add_color_to_links(xpander_use_cases)
    xpander_user_name = xpander_email.split("@")[0]
    
    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Replace all placeholders with provided parameters
        replacements = {
            '[[xpander_email]]': xpander_email,
            '[[xpander_user_name]]': xpander_user_name,
            '[[company_name]]': company_name.upper(),
            '[[base64_logo]]': str(base64_logo),
            '[[client_name]]': client_name,
            '[[now_date]]': now_date,
            '[[xpander_collaboration]]': agent_for_company,
            '[[xpander_use_cases]]': xpander_use_cases
        }
        
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)
            
        return html_content
        
    except FileNotFoundError:
        logger.error(f"Template file not found at {TEMPLATE_PATH}")
        raise
    except Exception as e:
        logger.error(f"Error processing template: {str(e)}")
        raise

def generate_qr_code(url: str) -> str:
    """
    Generates a QR code from a URL and returns it as a base64 encoded string.
    
    Args:
        url (str): The URL to encode in the QR code
        
    Returns:
        str: Base64 encoded string of the QR code image
    """

    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{qr_base64}"

def add_color_to_links(html_text: str, color: str = "#cc43ff") -> str:
    """
    Adds color styling to all HTML links in the text.
    
    Args:
        html_text (str): The HTML text containing links
        color (str): The color to apply to links (default: #cc43ff)
        
    Returns:
        str: Modified HTML text with colored links
    """
    import re
    
    # Pattern to match <a> tags that don't already have a style attribute
    pattern = r'<a\s+(?![^>]*style=)[^>]*?href=[^>]*?>'
    
    # Add style attribute with color
    replacement = lambda m: m.group(0).rstrip('>') + f' style="color: {color};">'
    
    # Replace all matching links
    modified_text = re.sub(pattern, replacement, html_text)
    
    return modified_text



def create_gmail_message(from_email, to_email, subject, link, company_name, client_name):
    html_template = email_template.format(link=link, company_name=company_name, subject=subject, client_name=client_name)
    return html_template
    # Create a MIMEText object with HTML content
    message = MIMEText(html_template, 'html')
    
    # Set the email headers
    message['To'] = to_email
    message['From'] = from_email
    message['Subject'] = subject

    # Convert the message to a string and encode it in base64url
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return raw_message

def get_all_tools_responses(xpander_agent, tool_select_response):
    tool_calls = XpanderClient.extract_tool_calls(tool_select_response.model_dump())
    responses = {}
    
    if tool_calls:
        with ThreadPoolExecutor() as executor:
            # Create future tasks for all tool calls
            future_to_tool = {
                executor.submit(xpander_agent.run_tool, tool_call): tool_call 
                for tool_call in tool_calls
            }
            
            # Process futures as they complete with progress bar
            with tqdm(total=len(tool_calls), desc="Running tools") as pbar:
                for future in as_completed(future_to_tool):
                    tool_response = future.result()
                    responses[tool_response.function_name] =  tool_response.result
                    pbar.update(1)

    tools = xpander_agent.get_tools()
    return responses, tools
