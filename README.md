# xpander-agents-hub

A comprehensive collection of examples and implementations demonstrating various ways to build and deploy AI agents using [xpander.ai](https://www.xpander.ai/).

## Overview

This repository serves as a hub for different implementation patterns of xpander AI agents, showcasing various architectures, deployment methods, and integrations with different LLM providers.

## Features

- 🐳 Standalone applications with Docker support
- 📓 Jupyter notebook examples
- 🤖 Multiple agent architectures
- 🔌 Integration examples with various LLM providers:
  - OpenAI
  - Anthropic
  - And more...

## Getting Started

1. Sign up at [xpander.ai](https://www.xpander.ai/)
2. Obtain your API credentials
3. Clone this repository:


bash
git clone https://github.com/yourusername/xpander-agents-hub.git

## Repository Structure


xpander-agents-hub/
├── notebooks/ # Jupyter notebooks with examples
├── standalone/ # Standalone application examples
│ └── docker/ # Dockerized implementations
├── architectures/ # Different agent architecture examples
└── providers/ # LLM provider-specific implementations

## Examples Include

- Basic agent implementation
- Multi-agent systems
- Agent orchestration
- Custom tool integration
- API connection examples

## Quick Example


python
```
import xpander_client
import openai
Initialize xpander client
xpander_client = xpander_client.Client(api_key="your-api-key")
Get available tools
tools = xpander_client.tools()
Create an agent with OpenAI
response = openai_client.chat.completions.create(
model="gpt-4",
messages=[{"role": "user", "content": "Your prompt here"}],
tools=tools,
tool_choice="auto"
)
Execute the agent's action
xpander_client.xpander_tool_call(response)
```

## Benefits of Using xpander

- 🚀 Rapid API integration through AI-ready connectors
- 📊 Automated graph generation for API dependencies
- 🔄 Simplified workflow creation
- 🛠️ Reduced development time
- 🔌 Easy integration with multiple LLM providers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

Copyright (c) 2024 [Your Name or Organization]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support

For support and questions:
- Visit [xpander.ai](https://www.xpander.ai/)
- Book a demo through the website
- Contact support through the platform

## Disclaimer

This is a community repository and is not officially maintained by xpander.ai.


