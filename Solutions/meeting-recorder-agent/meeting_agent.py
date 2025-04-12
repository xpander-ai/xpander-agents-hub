from xpander_sdk import XpanderClient, LLMProvider, Tokens, LLMTokens
from openai import OpenAI
import datetime
import time

class MeetingAgent:
    """Class for running the meeting recorder agent"""
    
    def __init__(self, openai_api_key, xpander_api_key, agent_id):
        self.agent_id = agent_id
        self.xpander_client = XpanderClient(api_key=xpander_api_key)
        # When running locally
        # self.xpander_client = XpanderClient(api_key="my-agent-controller-api-key", base_url="http://localhost:9991", organization_id="your-org-id")
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.agent = self.xpander_client.agents.get(agent_id=self.agent_id)
    
    def run(self, prompt=None, recordings_manager=None, thread_id=None):
        """Run the agent with the given prompt"""
        # Prepare agent task
        task = prompt or f"Now is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Please check the status of all recorded meetings."

        # Add existing recordings to the task if recordings_manager provided
        if recordings_manager:
            recordings_info = recordings_manager.get_recordings_info()
            if recordings_info:
                task = f"{task}\n\nHere are the all the recording bot IDs:\n{recordings_info}"

        print(f"Running agent to monitor changes or get a new task from the user")
        print(f"Agent prompt: \n\n{task}\n\n")
        print("-" * 60)
                
        # Create task with or without thread_id
        self.agent.add_task(input=task, thread_id=thread_id if thread_id else None)
        print(f"{'Continuing conversation in thread: ' + thread_id if thread_id else 'Starting a new conversation thread'}")
                
        # Initialize token tracking and timing
        execution_tokens = Tokens(worker=LLMTokens(completion_tokens=0, prompt_tokens=0, total_tokens=0))
        execution_start_time = time.perf_counter()
        
        # Run the agent until it's finished
        while not self.agent.is_finished():
            # Track start time for this inference
            start_time = time.perf_counter()
            
            # Get response from OpenAI and process
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=self.agent.messages,
                tools=self.agent.get_tools(llm_provider=LLMProvider.OPEN_AI),
                tool_choice=self.agent.tool_choice,
                temperature=0.0
            )
            
            # Track token usage
            execution_tokens.worker.completion_tokens += response.usage.completion_tokens
            execution_tokens.worker.prompt_tokens += response.usage.prompt_tokens
            execution_tokens.worker.total_tokens += response.usage.total_tokens
            
            # Report LLM usage to Xpander
            self.agent.report_llm_usage(
                llm_response=response.model_dump(),
                llm_inference_duration=time.perf_counter() - start_time,
                llm_provider=LLMProvider.OPEN_AI
            )
            
            self.agent.add_messages(response.model_dump())
            
            # Extract and execute any tool calls
            tool_calls = XpanderClient.extract_tool_calls(
                llm_response=response.model_dump(),
                llm_provider=LLMProvider.OPEN_AI
            )
            
            if tool_calls:
                self.agent.run_tools(tool_calls=tool_calls)
        
        # Process results
        execution_end_time = time.perf_counter()
        result = self.agent.retrieve_execution_result()
        thread_id = result.memory_thread_id
        print(f"Your thread ID is: {thread_id}")
        result_text = result.result
    
        # Report execution metrics to Xpander
        self.agent.report_execution_metrics(
            llm_tokens=execution_tokens,
            ai_model="gpt-4o"
        )
        
        print(f"Status: {result.status}")
        print(f"Result: {result_text}")
        print(f"Execution duration: {execution_end_time - execution_start_time:.2f} seconds")
    
        # Return both the result text and thread ID
        return result_text, thread_id 