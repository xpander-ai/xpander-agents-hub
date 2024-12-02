# Xpander.ai Graph-Based Streamlit Application

This Streamlit application integrates with Xpander.ai's graph functionality to [brief description of what your app does].

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:


```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

2.5. Install wkhtmltopdf
```base
brew install wkhtmltopdf
```

## Configuration

1. Create a `.env` file in the root directory of the project
2. Add the following environment variables:

```plaintext
OPENAI_API_KEY="your-openai-api-key"
XPANDER_API_KEY="your-xpander-api-key"
XPANDER_AGENT_ID="your-xpander-agent-id"
```

To obtain the necessary API keys:
- Get your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Get your Xpander API key and Agent ID from [Xpander.ai Dashboard](https://xpander.ai)

## Running the Application

1. Ensure you're in the project directory
2. Run the Streamlit application:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Features

[List the main features of your application]

## Usage

[Provide examples and screenshots of how to use your application]

## Troubleshooting

Common issues and their solutions:

1. **Environment Variables Not Loading**
   - Make sure the `.env` file is in the correct location
   - Verify the API keys are correctly formatted
   - Ensure no spaces around the "=" in the `.env` file

2. **Xpander.ai Graph Integration Issues**
   - Verify your Xpander API key is active
   - Confirm the Agent ID is correct
   - Check your network connection

## Contributing

[Instructions for how others can contribute to your project]

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


