# Xpander AI Research Assistant - Streamlit App

A powerful AI-powered research assistant that generates comprehensive reports by analyzing multiple sources including Tavily AI, LinkedIn, Perplexity, and ArXiv.

## Features

- 🔍 Comprehensive research across multiple sources
- 📚 Academic paper analysis from ArXiv
- 🌐 Web insights from Tavily AI
- 👥 Expert insights from LinkedIn
- 📝 Automated PDF report generation
- 💾 Research history tracking


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

## Usage

1. Ensure you're in the project directory
2. Start the Streamlit application:
```bash
streamlit run streamlit_app.py
```
3. Open your web browser and navigate to the provided URL (typically `http://localhost:8501`)
4. Enter your research query in the text input field
5. Click "Start Research" and wait for the assistant to generate your report

## Project Structure

agents/
└── use-cases/
└── research/
├── streamlit_app.py # Main Streamlit application
├── research_by_user_query.py # Research agent implementation
└── xpander_logo.jpeg # Application logo

## Dependencies

- Streamlit
- Pillow (PIL)
- Python 3.8+

## License

MIT License

## Support

For support and questions:
- Visit [xpander.ai](https://www.xpander.ai/)
- Book a demo through the website
- Contact support through the platform



