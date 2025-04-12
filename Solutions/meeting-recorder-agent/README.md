<div align="center">

# Meeting Recorder Agent

![Xpander.ai Logo (Dark Mode)](static/images/screenshots/Purple%20Logo%20White%20text.png#gh-dark-mode-only)
![Xpander.ai Logo (Light Mode)](static/images/screenshots/Purple%20Logo%20Black%20Text.png#gh-light-mode-only)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**A simple AI agent that records Google Meet meetings and tracks them automatically.**  
Built with [xpander.ai](https://xpander.ai)

[Key Features](#key-features) • [Quick Start](#quick-start) • [How It Works](#how-it-works) • [Usage](#usage) • [FAQ](#faq)

</div>

## 🌟 Key Features

- ✅ **Automated Recording** - Records Google Meet meetings without manual intervention
- 📊 **Meeting Management** - Keeps track of all your recorded meetings in one place
- 📝 **Content Generation** - Creates transcripts and downloadable video files
- 📅 **Calendar Integration** - Shows your calendar events with meeting statuses

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Meet account
- [Xpander.ai](https://xpander.ai) account

### Installation

```bash
# Clone and set up
git clone https://github.com/xpander-ai/meeting-recorder-agent.git
cd meeting-recorder-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your API keys:

```
OPENAI_API_KEY=your_openai_key
XPANDER_API_KEY=your_xpander_key
XPANDER_AGENT_ID=your_agent_id
```

## 📚 How It Works

The agent uses three main components:

1. **Main App (`app.py`)**: Coordinates everything and schedules checks
2. **Meeting Agent (`meeting_agent.py`)**: Connects to Xpander.ai to run the agent
3. **Recordings Manager (`recordings.py`)**: Tracks meetings in `recording_ids.json`

### Agent Tools

The template includes four independent tools:

#### 1. Check Recorder Status
Queries the status of recording bots and retrieves information about recordings:
- Shows if recordings are in progress or completed
- Provides links to video, audio, and transcript downloads
- Displays metadata like duration and participants

#### 2. Create Meeting Recording Bot
Creates and deploys a new bot to record a Google Meet session:
- Accepts Google Meet URLs in any format
- Automatically joins meetings using specified credentials
- Creates a dedicated recorder ID for tracking

#### 3. Send Email with Content
Sends meeting summaries and recordings via email:
- Sends transcript summaries to meeting participants
- Attaches or links to recording files
- Supports customized email templates

#### 4. Get Calendar Events by ID
Connects with your Google Calendar:
- Fetches upcoming and past calendar events
- Links calendar events to meeting recordings
- Provides scheduling information for the agent

## 🔍 Usage

Check all your recorded meetings:

```bash
python app.py
```

Record a specific meeting:

```bash
python app.py "please record meet.google.com/abc-defg-hij"
```

Check your calendar:

```bash
python app.py "what's on my calendar"
```

## 💾 Data Structure

The agent stores meeting information in `recording_ids.json`:

```json
{
  "67593763-9093-4fd4-88df-98c8bc75600a": {
    "url": "https://meet.google.com/dnj-wduu-goa"
  },
  "f4f81ac7-c28a-4831-8cfc-fa56e3c2b29c": {
    "url": "https://meet.google.com/gcd-zuba-qar"
  }
}
```

## 📊 Example Output

When you run the agent asking about calendar events:

```bash
python app.py "what's on my calendar"
```

It responds with:

```
Here are the events on your calendar and the status of the recording bots:

### Calendar Events:
1. **Onboarding to Xpander**
   - Date & Time: April 9, 2025, 17:31 - 18:31 UTC
   - [Event Link](https://www.google.com/calendar/event?eid=...)

2. **Meeting with David about xpander**
   - Date & Time: April 9, 2025, 20:27 - 21:27 UTC
   - [Event Link](https://www.google.com/calendar/event?eid=...)

### Recording Bots Status:
1. **Recorder ID: 67593763-9093-4fd4-88df-98c8bc75600a**
   - Status: Done
   - Meeting URL: [meet.google.com/dnj-wduu-goa](https://meet.google.com/dnj-wduu-goa)
   - Video: [Download MP4](https://links.xpander.ai/jz0zr6w)
   - Transcript: [Download TXT](https://links.xpander.ai/kb42drv)
```

## 🔍 Monitoring

You can use the xpander.ai platform to monitor the logs of the agent:

![Xpander Dashboard](static/images/screenshots/2025-04-12-12-27-31.png)

## 👨‍💻 Built With Xpander.ai

[Xpander.ai](https://xpander.ai) is an AI Agent platform that lets developers build, test, and deploy AI agents quickly. It provides:

- **State Management**: Handles complex agent states so you don't have to
- **Provider Independence**: Works with OpenAI, Anthropic, Gemini, and more
- **Tool Integration**: Easy calendar, meeting, and custom tool integration

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

Questions? Reach out to us at [support@xpander.ai](mailto:support@xpander.ai)
