from xpander_sdk import XpanderClient, LLMProvider
from openai import OpenAI
import datetime

class MeetingAgent:
    """Class for running the meeting recorder agent"""
    
    def __init__(self, openai_api_key, xpander_api_key, agent_id):
        self.agent_id = agent_id
        self.xpander_client = XpanderClient(api_key=xpander_api_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
    
    def run(self, prompt=None, recordings_manager=None):
        """Run the agent with the given prompt"""
        # Prepare agent task
        task = prompt or f"Now is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Please check the status of all recorded meetings."

        # Add existing recordings to the task if recordings_manager provided
        if recordings_manager:
            recordings_info = recordings_manager.get_recordings_info()
            if recordings_info:
                task = f"{task}\n\nHere are the all the recording bot IDs:\n{recordings_info}"

        print(f"Running agent to monitor changes in the recordings DB or get a new task from the user")
        print(f"Agent prompt: \n\n{task}\n\n")
        print("-" * 60)
        
        # Get and run the agent
        agent = self.xpander_client.agents.get(agent_id=self.agent_id)
        agent.add_task(task)
        
        # Run the agent until it's finished
        while not agent.is_finished():
            try:
                # Get response from OpenAI and process
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=agent.messages,
                    tools=agent.get_tools(llm_provider=LLMProvider.OPEN_AI),
                    tool_choice=agent.tool_choice,
                    temperature=0.0
                )
                
                agent.add_messages(response.model_dump())
                
                # Extract and execute any tool calls
                tool_calls = XpanderClient.extract_tool_calls(
                    llm_response=response.model_dump(),
                    llm_provider=LLMProvider.OPEN_AI
                )
                
                if tool_calls:
                    agent.run_tools(tool_calls=tool_calls)
            except Exception as e:
                print(f"Error running agent: {e}")
                break
        
        # Process results
        result = agent.retrieve_execution_result()
        result_text = result.result
        print(f"Result: {result_text}")
        
        # Process recordings if manager provided
        if recordings_manager:
            recordings_manager.process_results(result_text)
            
        return result_text 