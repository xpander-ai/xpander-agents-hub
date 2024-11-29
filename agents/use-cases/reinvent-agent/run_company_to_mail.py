import asyncio
from email.mime.text import MIMEText
from loguru import logger
import requests
from xpander_sdk import XpanderClient, Agent
from dotenv import load_dotenv
import os
import time
import sys
from pathlib import Path
import qrcode
import base64
from io import BytesIO
import yaml
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents_util.handler.gpt_handle import OpenAIHandler
from agents_util.utils.generic import *
from prompts import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

load_dotenv()
OUTPUT_PATH = Path(__file__).parent / "collaboration_file.html"
logo_path = Path(__file__).parent / 'logo.jpg'
template_path = Path(__file__).parent / 'reInvent_template.html'
xpanderClient = XpanderClient(api_key=os.environ.get("XPANDER_API_KEY", ""))

def split_companies_information(retrieval_tool_results, company):
    xpander_ai_info = ""
    company_info = ""
    for tool_name, tool_result in retrieval_tool_results.items():
        tool_result_str = yaml.dump(tool_result, indent=2)
        if "notion" in tool_name.lower():
            xpander_ai_info = tool_result_str
        else:
            company_info += f"{tool_name} information about the company {company}:\n{tool_result_str}\n"
    logo_url = retrieval_tool_results.get('LinkedInCompanyManagementGetCompanyDetailsByUsername', {}).get('data', {}).get('Images', {}).get('logo')
    return xpander_ai_info, company_info, logo_url

def split_text_to_rows(text: str, target_length: int = 100) -> str:
    """
    Splits a string into rows of approximately target_length characters,
    breaking at sentence boundaries (periods) and word boundaries.
    Treats HTML links as single words, counting only the visible text.
    
    Args:
        text (str): The input text to split
        target_length (int): Target length for each row (default: 100)
        
    Returns:
        str: Text split into rows with line breaks
    """
    # First split into sentences
    text = text.strip("\n")
    sentences = text.replace('. ', '.|').split('|')
    
    rows = []
    current_row = []
    current_length = 0
    
    for sentence in sentences:
        # Split by spaces but preserve HTML tags
        words = []
        current_word = []
        in_tag = False
        
        for char in sentence:
            if char == '<':
                in_tag = True
                current_word.append(char)
            elif char == '>':
                in_tag = False
                current_word.append(char)
                if char == '>' and ' ' in ''.join(current_word):
                    words.append(''.join(current_word))
                    current_word = []
            elif char == ' ' and not in_tag:
                if current_word:
                    words.append(''.join(current_word))
                    current_word = []
            else:
                current_word.append(char)
        
        if current_word:
            words.append(''.join(current_word))
        
        for word in words:
            # Extract visible text length for HTML links
            visible_length = len(word)
            if word.startswith('<a') and word.endswith('</a>'):
                # Extract text between > and <
                visible_text = word[word.find('>')+1:word.rfind('<')]
                visible_length = len(visible_text)
            
            # Length if we add this word (including space)
            word_length = visible_length + (1 if current_row else 0)
            
            if current_length + word_length > target_length and current_row:
                # Join current row and add it to rows
                rows.append(' '.join(current_row))
                current_row = [word]
                current_length = visible_length
            else:
                current_row.append(word)
                current_length += word_length
        
        # After processing each sentence, force a new line if there's content
        if current_row:
            rows.append(' '.join(current_row))
            current_row = []
            current_length = 0
    
    return '\n'.join(filter(None, rows))

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
    agent_for_company = split_text_to_rows(agent_for_company)
    xpander_use_cases = extract_html_content(xpander_use_cases)
    xpander_use_cases = xpander_use_cases.strip("\n")
    xpander_use_cases = split_text_to_rows(xpander_use_cases)
    xpander_user_name = xpander_email.split("@")[0]
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            
        # Replace all placeholders with provided parameters
        replacements = {
            '[[xpander_email]]': xpander_email,
            '[[xpander_user_name]]': xpander_user_name,
            '[[company_name]]': company_name,
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
        logger.error(f"Template file not found at {template_path}")
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


async def run_company_query(company, xpander_employee_email=None, email=None, client_name=None):
    """
    Executes a comprehensive analysis of a company using various agents and tools.

    Args:
        company (str): Name of the company to analyze
        model (str): Name of the AI model to u  se for analysis

    Returns:
        dict: Metadata containing analysis results, including token counts,
             number of steps, and execution time
    """
    xpander_agent : Agent = xpanderClient.agents.get(agent_id=os.environ.get("XPANDER_AGENT_ID", ""))
    start_time = time.time()
    tools = xpander_agent.get_tools()
    handler = OpenAIHandler(model_name="gpt-4o-mini")
    topic_response, topic_metadata = handler.agent_inference(message=[{"role": "user", "content": system_prompt_graph_decision}], tmp_tools=tools, tool_choice="required")
    topic = XpanderClient.extract_tool_calls(topic_response.model_dump())
    _ = xpander_agent.run_tool(tool=topic[0])
    logger.info(f"Topic: {topic[0].name}")
    tools = xpander_agent.get_tools()
    handler = OpenAIHandler(model_name="gpt-4o")
    logger.info(f"Starting retrieval agent")
    retrieval_response, retrieval_metadata = handler.agent_inference(message=[{"role": "user", "content": retrieval_agent_prompt.format(company=company)}], tmp_tools=tools, tool_choice="required")
    retrieval_tool_results, tools = get_all_tools_responses(xpander_agent, retrieval_response)
    logger.info(f"Retrieval agent completed")
    xpander_ai_info, company_info, logo_url = split_companies_information(retrieval_tool_results, company)
    logger.info(f"Now we have the information about {company} and xpander ai")
    company_collaboration_response, company_collaboration_metadata = handler.agent_inference(message=[{"role": "user", "content": collaborate_agent_prompt.format(company=company, company_info=company_info, xpander_ai_info=xpander_ai_info)}], tmp_tools=None, tool_choice=None)
    use_cases_response, use_cases_metadata = handler.agent_inference(message=[{"role": "user", "content": use_cases_agent_prompt.format(company=company, company_info=company_info, xpander_ai_info=xpander_ai_info)}], tmp_tools=None, tool_choice=None)
    html_content = create_html_by_template(xpander_email=xpander_employee_email, company_name=company, client_name=client_name, agent_for_company=company_collaboration_response, xpander_use_cases=use_cases_response, logo_url=logo_url)

    upload_s3_response, upload_s3_metadata = handler.agent_inference(message=[{"role": "user", "content": f"please convert this text to pdf: 'Hello World'"}], tmp_tools=tools, tool_choice="required")
    escaped_html = json.dumps(html_content)[1:-1]  # Remove the outer quotes that dumps adds
    upload_s3_response.choices[0].message.tool_calls[0].function.arguments = '{{"bodyParams":{{"content":"{}", "file_type": "html"}},"queryParams":{{}},"pathParams":{{}}}}'.format(escaped_html)
    s3_results, tools = get_all_tools_responses(xpander_agent, upload_s3_response)
    presigned_url = s3_results['uploadToS3']['presigned_url']
    qr_code_base64 = generate_qr_code(presigned_url)

    email_response, email_metadata = handler.agent_inference(message=[{"role": "user", "content": send_email_prompt}], tmp_tools=tools, tool_choice="required")
    gmail_raw = create_gmail_message(from_email=xpander_employee_email, to_email=email, subject='Welcome to xpander.ai booth', link=presigned_url, company_name=company)
    email_response.choices[0].message.tool_calls[0].function.arguments = '{{"bodyParams":{{"raw":"{}"}},"queryParams":{{}},"pathParams":{{"userEmail":"me"}}}}'.format(gmail_raw)
    email_tool_results, tools = get_all_tools_responses(xpander_agent, email_response)
    logger.info(f"Draft tool results: {email_tool_results}")
    
    return qr_code_base64

def create_gmail_message(from_email, to_email, subject, link, company_name):
    html_template = email_template.format(link=link, company_name=company_name)
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


# asyncio.run(run_company_query(company="Nvidia", xpander_employee_email="shaked@xpander.ai", email="shaked@xpander.ai", client_name="test"))
