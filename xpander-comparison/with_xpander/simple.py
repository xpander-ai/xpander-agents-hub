from xpander_sdk import XpanderClient, LLMProvider 
from openai import OpenAI
import json
## Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()
OpenAPIKey = os.environ.get("OPENAI_API_KEY","")
xpanderAPIKey = os.environ.get("XPANDER_API_KEY","")
xpanderAgentURL = os.environ.get("XPANDER_AGENT_URL","")

## Initialize OpenAI and Xpander clients
openai_client = OpenAI(api_key=OpenAPIKey)

xpander_client = XpanderClient(
    agent_key=xpanderAPIKey, 
    agent_url=xpanderAgentURL, 
    llm_provider=LLMProvider.OPEN_AI
)

## Only needed if you want to use the session API to enforce specific behavior of prompt group to subgraph
xpander_client.start_session(prompt="Events managements")

agent_memory = []
tool_memory = []

# Explain the AI the graph structure and the tools available
agent_memory.append({"role": "system", "content": "You are a helpful assistant, you are running in While loop and will have access to invoke tools dynmaically to your location in the graph. If you want to stop the loop, please add ##FINAL ANSWER## in your answer"})

task  ='''
High level task: Conduct a deep dive research about {company_name} , with key personas and anaylsis on the data collected. The anaylsis must be saved in a new page in the “Companies Analysis” ID is 13029ef830b380f29f01e28f5968a9e4 database table in Notion.How to do it?:- Make sure to follow the notion database structure first and understand the data structure.- Find all the recent news about the company and the relevant websites urls using tavily, tweeter, crunchbase and linkedin and any other tools you need that might be relevant and available.- Summarize the data collected about the companyThe final answer must include a link to the new notion page, you must use all the resources when you creating the final pagestart!

For crunchbase, you should send the company name as the query not the domain name.
'''

agent_memory.append({"role": "user", "content": task.format(company_name="composio.ai")})
number_of_calls = 1

while True:
    agent_response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=agent_memory,
        tools=xpander_client.tools(), ## all the tools 
        tool_choice="auto", 
        max_tokens=1024,
    )

    agent_memory.append({"role": "assistant", "content": f'Step number: {number_of_calls}'})
    
    for agent_choice in agent_response.choices:
        agent_memory.append(agent_choice.message)
        
        if(agent_choice.message.tool_calls):
            for tool_call in agent_choice.message.tool_calls:
                try:
                    tool_response = xpander_client.xpander_single_tool_invoke(tool_id=tool_call.function.name,payload=json.loads(tool_call.function.arguments))
                except Exception as e:
                    print(e)
                    tool_response = f"Error calling the tool {tool_call.function.name}. Error is {e}"
                    pass

                parser_message = [{"role": "user", "content": f"Your task is to parse the data for Planner Agent from the tool call and extract the information needed to answer the user request. Tool call: {tool_call.function.name}. Response from the tool: {tool_response}"}]

                parser_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=parser_message
                )
                
                for parser_choice in parser_response.choices:
                    function_call_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": parser_choice.message.content
                    }
                    agent_memory.append(function_call_result_message)
        
    if (agent_response.choices[0].message.content):
        if "##FINAL ANSWER##" in agent_response.choices[0].message.content:
            break
    number_of_calls += 1

# Print the final answer
print(agent_response.choices[0].message.content)
