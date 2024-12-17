import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from xpander_sdk import XpanderClient, OpenAISupportedModels
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from prompts import *

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def initialize_clients():
    """
    Initialize OpenAI and Xpander clients using environment variables.
    Returns:
        tuple: (OpenAI client, Xpander client, Xpander agent)
    """
    # Load environment variables from .env
    load_dotenv()
    
    # Initialize API clients
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    xpander_client = XpanderClient(api_key=os.environ.get("XPANDER_API_KEY", ""))
    xpander_agent = xpander_client.agents.get(agent_id=os.environ.get("XPANDER_AGENT_ID", ""))
    
    return openai_client, xpander_client, xpander_agent

def initialize_sub_graph(xpander_client, xpander_agent,openai_client):
    """
    Initialize the sub-graph for the research agent.
    """
    tools = xpander_agent.get_tools()
    sub_graph_response = openai_client.chat.completions.create(
    model=OpenAISupportedModels.GPT_4_O,
    messages=[{"role": "user", "content": "return your input tools with the correct args"}],
    tools=tools,
    tool_choice="required",
    parallel_tool_calls=False,
    temperature=0.0
    )
    
    # Extract and run tool calls
    sub_graph_name = xpander_client.extract_tool_calls(llm_response=sub_graph_response.model_dump())
    _ = xpander_agent.run_tools(sub_graph_name)
    logger.info(f"sub graph {sub_graph_name[0].name} initialized")
 

def research_by_user_query_parallel(user_query,progress_callback=None):
    """
    Conduct research based on user query and generate a PDF report.
    Args:
        user_query (str): The research query from the user
    Returns:
        str: Presigned URL of the generated PDF report
    """
    # Initialize clients
    openai_client, xpander_client, xpander_agent = initialize_clients()
    initialize_sub_graph(xpander_client, xpander_agent,openai_client)
    tools = xpander_agent.get_tools()
    logger.info(f"Starting retrieval agent")
    
    if progress_callback:
        progress_callback("initialization")
    
    # Generate research queries using retrieval agent
    retrieval_agent_response = openai_client.chat.completions.create(
    model=OpenAISupportedModels.GPT_4_O,
    messages=[{"role": "user", "content": retrieval_agent_prompt.format(user_query=user_query)}],
    tools=tools,
    tool_choice="required",
    parallel_tool_calls=True,
    temperature=0.0
    )
    
    if progress_callback:
        progress_callback("research")
    
    tool_calls = xpander_client.extract_tool_calls(llm_response=retrieval_agent_response.model_dump())
    responses = {}
    
    if tool_calls:
        with ThreadPoolExecutor() as executor:
            # Create parallel tasks for tool execution
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
    logger.info("finishes gathering all research data")                
    logger.info(f"Tool responses: {responses}")
    
    if progress_callback:
        progress_callback("report_creation")
    # Generate research report using collected data
    report_creation_agent_response = openai_client.chat.completions.create(
    model=OpenAISupportedModels.GPT_4_O,
    messages=[{"role": "user", "content": report_creation_agent_prompt.format(user_query=user_query, user_query_info=responses)}],
    temperature=0.0,
    max_tokens=16384
    )
    
    report_content=report_creation_agent_response.choices[0].message.content
    logger.info(f"Report creation agent response: {report_content}")
    
    if progress_callback:
        progress_callback("pdf-operations-convertMarkdownToPDF")
        
    # Convert markdown report to PDF
    pdf_response = openai_client.chat.completions.create(
    model=OpenAISupportedModels.GPT_4_O,
    messages=[{"role": "user", "content": f"convert the following markdown report to pdf: {report_creation_agent_response.choices[0].message.content}"}],
    tools=xpander_agent.get_tools(),
    tool_choice="required",
    parallel_tool_calls=False,
    temperature=0.0
    )  
    
    tool_calls = xpander_client.extract_tool_calls(llm_response=pdf_response.model_dump())
    if tool_calls:
        logger.info(f"Tool calls: {tool_calls[0].name}")
        tool_response = xpander_agent.run_tool(tool_calls[0])
        
        if isinstance(tool_response.result, dict) and 'presigned_url' in tool_response.result:
            logger.info("PDF generation complete! URL: %s", tool_response.result['presigned_url'])
            pdf_url=tool_response.result['presigned_url']
            
            if progress_callback:
                progress_callback("completion")
        return pdf_url

    return None

    