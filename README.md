<div align="center">
  <h1>🤖 XPander Agents Hub</h1>
  <p><strong>Examples and Templates for Building AI Agents with xpander.ai</strong></p>
  <a href="https://www.xpander.ai">
    <img src="https://img.shields.io/badge/powered%20by-XPander-blue" alt="Powered by xpander.ai">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License">
  </a>
  <a href="https://www.xpander.ai/docs">
    <img src="https://img.shields.io/badge/docs-latest-orange" alt="Platform Documentation">
  </a>
</div>

<hr>

## Overview

This repository contains examples, templates, and best practices for building and managing AI agents using the xpander.ai platform. Whether you're migrating existing agents or building new ones, you'll find resources to help you leverage xpander.ai's state management capabilities.

### Featured Solution: Meeting Recorder Agent

Our [Meeting Recorder Agent](Solutions/meeting-recorder-agent/) is a production-ready solution that:
- Automatically records Google Meet sessions
- Generates transcripts and downloadable videos
- Tracks meeting history and calendar events
- Provides a complete demonstration of xpander.ai's capabilities

## What's Inside

### Getting Started

- Quick setup guides for connecting your first agent
- Configuration templates for different use cases
- Best practices for state management

### Sample Implementations

- Integration examples with popular frameworks
- LLM provider configurations
- Real-world use cases and patterns

### Solutions

- Complete, production-ready agent implementations
- End-to-end examples with real-world utility
- Ready-to-deploy templates for common use cases

## Repository Structure

```
.
├── Getting-Started/  # Notebooks for getting started with xpander.ai
├── Samples/
│   ├── Frameworks/           # Framework integrations
│   │   ├── chainlit/           # Chainlit examples
│   │   └── langchain/          # LangChain examples
│   └── LLM-Providers/        # LLM configuration examples
│   │   ├── amazon/              # Amazon Bedrock examples
│   │   ├── openai/           # OpenAI examples
│   │   └── nvidia/          # Nvidia examples
├── Solutions/               # Complete, production-ready solutions
│   └── meeting-recorder-agent/  # Agent for recording Google Meet sessions
└── Use-Cases/               # Industry-specific implementations
```

## Quick Start

The xpander.ai platform manages state transitions and multi-agent orchestration automatically. Here's how to integrate with it:

### 1. Setting Up Your Environment

```python
from xpander_sdk import XpanderClient, ToolCallResult
from openai import OpenAI
from dotenv import load_dotenv
from os import environ

load_dotenv()

# Configure your API keys
OPENAI_API_KEY = environ["OPENAI_API_KEY"]
XPANDER_API_KEY = environ["XPANDER_API_KEY"]
XPANDER_AGENT_ID = environ["XPANDER_AGENT_ID_MULTI"]

# Initialize clients
xpander_client = XpanderClient(api_key=XPANDER_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
```

### 2. State Management and Multi-Agent Execution

```python
# Load the agent - xpander.ai manages its state and available tools
agent = xpander_client.agents.get(agent_id=XPANDER_AGENT_ID)

# Add a task - this initializes the execution state
agent.add_task("""
Search for 2 startups in the AI sector and get LinkedIn profiles of their founders.
""")

# Initialize agent's memory with context and instructions
# This sets up the initial state and available tools
agent.memory.init_messages(input=agent.execution.input_message, instructions=agent.instructions)

# The state machine loop - xpander.ai handles:
# - State transitions between agents
# - Tool availability per state
# - Context preservation
# - Execution scheduling
while not agent.is_finished():
    # Each iteration may involve different agents based on the current state
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=agent.messages,  # Contains state-specific context
        tools=agent.get_tools(),  # Tools available in current state
        tool_choice=agent.tool_choice,
        temperature=0.0
    )
        
    # Update agent state with new messages
    agent.add_messages(response.model_dump())
    
    # Execute tools based on current state permissions
    tool_calls = XpanderClient.extract_tool_calls(llm_response=response.model_dump())
    agent.run_tools(tool_calls=tool_calls)
    # xpander.ai automatically:
    # - Validates tool permissions
    # - Manages state transitions
    # - Preserves context between states
    # - Schedules next agent if needed

# Retrieve final results across all agent states
execution_result = agent.retrieve_execution_result()
print("Status:", execution_result.status)
print("Result:", execution_result.result)
```

### 3. Environment Configuration

Create a `.env` file in your project root:

```bash
OPENAI_API_KEY=your_openai_api_key
XPANDER_API_KEY=your_xpander_api_key
XPANDER_AGENT_ID_MULTI=your_agent_id
```

### Handling High-Volume Tasks from Multiple Sources

In enterprise environments, AI agents often need to handle hundreds of concurrent tasks from various sources:
- Slack messages and commands
- Web UI interactions
- REST API calls
- Webhook events
- Third-party integrations

This creates several challenges that xpander.ai's state management solves:

1. **Task Queuing and Prioritization**
  
```python
# Tasks can come from multiple sources simultaneously
agent.add_task(
    input="Analyze customer feedback",
    source="slack",
    priority="high",
    metadata={
        "channel": "customer-support",
        "requester": "support-team"
    }
)

# xpander.ai handles:
# - Task prioritization
# - Resource allocation
# - State preservation for long-running tasks
```

2. **Long-Running Task Management**

```python
# Tasks can be paused and resumed across sessions
task_id = agent.add_task("Generate quarterly report")

# Even if the task takes days and requires external input
# xpander.ai maintains state and context
status = agent.get_task_status(task_id)
if status.awaiting_input:
    agent.provide_task_input(task_id, user_input)
```

3. **Concurrent Execution with State Isolation**

```python
# Multiple tasks can run concurrently
# Each with its own isolated state and context
tasks = [
    agent.add_task("Task from Slack", source="slack"),
    agent.add_task("Task from Web", source="web_ui"),
    agent.add_task("Task from API", source="rest_api")
]

# xpander.ai ensures:
# - No state contamination between tasks
# - Proper resource allocation
# - Consistent tool access per state
```

4. **Source-Specific State Handling**

```python
# Different sources may require different state machines
agent.add_task(
    input="Process data",
    source_config={
        "type": "slack",
        "state_machine": "interactive",  # Handles user interactions
        "timeout": 3600  # Long-running tasks
    }
)

agent.add_task(
    input="Quick analysis",
    source_config={
        "type": "api",
        "state_machine": "batch",  # Optimized for batch processing
        "timeout": 300  # Short-lived tasks
    }
)
```

5. **Task Recovery and Persistence**

```python
# xpander.ai automatically handles:
# - Task interruptions
# - System restarts
# - Network issues
# - Session timeouts

# Tasks can be resumed from their last valid state
interrupted_tasks = agent.get_interrupted_tasks()
for task in interrupted_tasks:
    agent.resume_task(task.id)  # State and context automatically restored
```

### State Management Details

The xpander.ai platform handles several key aspects automatically:

1. **State Transitions**
   - Automatically determines when to switch between agents
   - Preserves context across transitions
   - Manages tool access permissions per state

2. **Multi-Agent Orchestration**
   - Schedules appropriate agents based on task requirements
   - Maintains conversation context across agent switches
   - Handles parallel execution when possible

3. **Context Management**
   - Preserves memory and context between state transitions
   - Manages tool availability based on current state
   - Ensures consistent execution across state changes

4. **Execution Flow**
   - Validates tool calls against state permissions
   - Manages agent scheduling and transitions
   - Handles error states and recovery

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.