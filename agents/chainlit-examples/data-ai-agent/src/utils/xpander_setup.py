import json
from typing import List, Dict, Any
from xpander_sdk import XpanderClient, ToolCallType

from src.config.settings import XPANDER_API_KEY, XPANDER_AGENT_ID

class XpanderSetup:
    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        self.client = XpanderClient(api_key=XPANDER_API_KEY)
        self.agent = self.client.agents.get(agent_id=XPANDER_AGENT_ID)
        self._setup_tools()

    def _setup_tools(self):
        """Setup local tools in Xpander agent"""
        local_tools = self.tool_manager.get_local_tools()
        self.agent.add_local_tools(local_tools)

    def get_distinct_tools(self) -> List[Dict[str, Any]]:
        """Get combined and deduplicated tools from both sources"""
        tools_from_get_tools = self.agent.get_tools()
        tools_from_retrieve_graph_tools = self.agent.retrieve_all_graph_tools()

        # Combine both arrays
        combined_tools = tools_from_get_tools + tools_from_retrieve_graph_tools

        # Use a list to keep unique dictionaries
        distinct_tools = []
        seen = set()

        for tool in combined_tools:
            # Serialize the dictionary to a JSON string to make it hashable
            tool_serialized = json.dumps(tool, sort_keys=True)
            if tool_serialized not in seen:
                seen.add(tool_serialized)
                distinct_tools.append(tool)

        return distinct_tools

    def extract_tool_calls(self, llm_response):
        """Extract tool calls from LLM response"""
        return XpanderClient.extract_tool_calls(llm_response=llm_response.model_dump())

    def run_tool(self, tool_call):
        """Run a tool using Xpander agent"""
        return self.agent.run_tool(tool_call) 