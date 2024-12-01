import asyncio
from loguru import logger
from xpander_sdk import XpanderClient, Agent
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents_util.handler.gpt_handle import OpenAIHandler
from agents_util.utils.generic import *
from prompts import *
from utils import *

load_dotenv()
xpanderClient = XpanderClient(api_key=os.environ.get("XPANDER_API_KEY", ""))
xpander_agent: Agent = xpanderClient.agents.get(agent_id=os.environ.get("XPANDER_AGENT_ID", ""))
    
async def run_company_query(company, company_domain, xpander_employee_email=None, email=None, client_name=None):
    """
    Executes a comprehensive analysis of a company using various agents and tools.

    Args:
        company (str): Name of the company to analyze
        model (str): Name of the AI model to u  se for analysis

    Returns:
        dict: Metadata containing analysis results, including token counts,
             number of steps, and execution time
    """
    
    tools = xpander_agent.get_tools()
    handler = OpenAIHandler(model_name="gpt-4o-mini")
    topic_response, _ = handler.agent_inference(message=[{"role": "user", "content": system_prompt_graph_decision}], tmp_tools=tools, tool_choice="required")
    topic = XpanderClient.extract_tool_calls(topic_response.model_dump())
    _ = xpander_agent.run_tool(tool=topic[0])
    logger.info(f"Topic: {topic[0].name}")
    tools = xpander_agent.get_tools()
    handler = OpenAIHandler(model_name="gpt-4o")
    logger.info(f"Starting retrieval agent")
    retrieval_response, _ = handler.agent_inference(message=[{"role": "user", "content": retrieval_agent_prompt.format(company=company, company_domain=company_domain)}], tmp_tools=tools, tool_choice="required")
    retrieval_tool_results, tools = get_all_tools_responses(xpander_agent, retrieval_response)
    logger.info(f"Retrieval agent completed")
    xpander_ai_info, company_info, logo_url = split_companies_information(retrieval_tool_results, company)
    logger.info(f"Now we have the information about {company} and xpander ai")
    company_collaboration_response, _ = handler.agent_inference(message=[{"role": "user", "content": collaborate_agent_prompt.format(company=company, company_info=company_info, xpander_ai_info=xpander_ai_info)}], tmp_tools=None, tool_choice=None)
    use_cases_response, _ = handler.agent_inference(message=[{"role": "user", "content": use_cases_agent_prompt.format(company=company, company_info=company_info, xpander_ai_info=xpander_ai_info)}], tmp_tools=None, tool_choice=None)
    html_content = create_html_by_template(xpander_email=xpander_employee_email, company_name=company, client_name=client_name, agent_for_company=company_collaboration_response, xpander_use_cases=use_cases_response, logo_url=logo_url)

    upload_s3_response, _ = handler.agent_inference(message=[{"role": "user", "content": f"please upload the following html content to s3: '{basic_html}'"}], tmp_tools=tools, tool_choice="required")
    escaped_html = json.dumps(html_content)[1:-1]  # Remove the outer quotes that dumps adds
    
    upload_s3_response.choices[0].message.tool_calls[0].function.arguments = '{{"bodyParams":{{"content":"{}", "file_type": "html"}},"queryParams":{{}},"pathParams":{{}}}}'.format(escaped_html)
    
    s3_results, tools = get_all_tools_responses(xpander_agent, upload_s3_response)
    
    presigned_url = s3_results['uploadToS3']['presigned_url']
    qr_code_base64 = generate_qr_code(presigned_url)

    email_response, _ = handler.agent_inference(message=[{"role": "user", "content": send_email_prompt}], tmp_tools=tools, tool_choice="required")
    
    mail_subject ='Thank you for visiting xpander.ai booth re:Invent 2024'
    if client_name:
        mail_subject = f"{client_name}, {mail_subject}"
    
    email_html_content = create_gmail_message(from_email=xpander_employee_email, to_email=email, subject=mail_subject, link=presigned_url, company_name=company, client_name=client_name if client_name else "")
    
    email_response.choices[0].message.tool_calls[0].function.arguments = json.dumps({"bodyParams":{"subject":mail_subject,"to":[email],"body_html":email_html_content},"queryParams":{},"pathParams":{}})
    _, tools = get_all_tools_responses(xpander_agent, email_response)  
    logger.info("Finished Company Collaboration Email")
    
    return qr_code_base64
