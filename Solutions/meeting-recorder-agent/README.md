<div align="center">

# Meeting Recorder Agent

![xpander.ai Logo (Dark Mode)](static/images/screenshots/Purple%20Logo%20White%20text.png#gh-dark-mode-only)
![xpander.ai Logo (Light Mode)](static/images/screenshots/Purple%20Logo%20Black%20Text.png#gh-light-mode-only)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**A simple AI agent that records Google Meet meetings and tracks them automatically.**  
Built with [xpander.ai](https://xpander.ai)

[Key Features](#-key-features) • [Demo](#demo-using-the-xpander-agent-workbench-ui) • [Quick Start](#-quick-start) • [How It Works](#-how-it-works) • [Usage](#-usage) • [Monitoring](#-monitoring)

</div>

## 🌟 Key Features

- ✅ **Automated Recording** - Records Google Meet meetings without manual intervention
- 📊 **Meeting Management** - Keeps track of all your recorded meetings in one place
- 📝 **Content Generation** - Creates transcripts and downloadable video files
- 📅 **Calendar Integration** - Shows your calendar events with meeting statuses

## DEMO (Using the xpander Agent Workbench UI)

<div align="center">
  <img src="static/images/screenshots/2025-04-12-13-31-22.png" alt="Meeting Recorder Demo 1" width="800">
  <p><em>Ask the agent to record a new meeting by providing the Google Meet URL</em></p>
  
  <img src="static/images/screenshots/2025-04-12-13-30-49.png" alt="Meeting Recorder Demo 2" width="800">
  <p><em>Approve the recording bot to join your Google Meet session</em></p>
  
  <img src="static/images/screenshots/2025-04-12-13-33-18.png" alt="Meeting Recorder Demo 3" width="800">
  <p><em>Ask the agent to retrieve the meeting transcript and video recording</em></p>
</div>

## 🚀 Quick Start

This guide will help you set up and run the Meeting Recorder Agent. For a comprehensive introduction to building agents with xpander.ai, check out the [Quickstart Workbench Guide](https://docs.xpander.ai/docs/01-get-started/02-getting-started-01-workbench).

### Prerequisites

- Python 3.8+
- Google Meet account
- [xpander.ai](https://xpander.ai) account

### Installation

```bash
# Clone and set up
git clone https://github.com/xpander-ai/xpander-agents-hub
cd xpander-agents-hub/Solutions/meeting-recorder-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Setting Up Your Agent

You have two options to set up the agent on xpander.ai:

#### Option 1: Use the Template (Recommended)

1. Log in to your [app.xpander.ai](https://app.xpander.ai) account
2. Inside "Agents" Click on Templates and select "Meeting Recorder Template"
3. Click "Import Template" to add it to your workspace
4. Once imported, from the AI Agent Workbench, click on the SDK Trigger
5. Copy your **Agent ID** and **API Key**

Learn more about getting started with xpander workbench in the [official documentation](https://docs.xpander.ai/docs/01-get-started/02-getting-started-01-workbench).

#### Option 2: Manual Setup

If you prefer to build the agent manually:

1. Log in to your [app.xpander.ai](https://xpander.ai) account
2. Click "Create New Agent" from your dashboard and skip the Planner step
3. Add the following tools to your agent from the Built-in actions menu:
   - **Check Recorder Status** tool
   - **Create Meeting Recording Bot** tool
   - **Send Email with Content** tool
4. Add the following tool to your agent from the Google Calendar app:
   - **Get Calendar Events by ID** tool
5. Save your agent and copy your **Agent ID** and **API Key** from the SDK Trigger

For detailed instructions on adding tools to your agent, refer to the [Adding Tools to Agents](https://docs.xpander.ai/docs/02-agent-builder/02-add-tools-to-agents) documentation.

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

The agent uses two main components:

1. **Main App (`app.py`)**: Coordinates everything and schedules checks every 5 minutes
2. **Meeting Agent (`meeting_agent.py`)**: Connects to xpander.ai to run the agent

The agent leverages xpander.ai's built-in thread-based memory system to maintain conversation context and remember meeting details across sessions.

### Agent Tools

<table>
<tr>
  <td width="25%" align="center">
    <h4>🔎<br>Check Recorder Status</h4>
  </td>
  <td>
    Queries the status of recording bots and retrieves information about recordings:
    <ul>
      <li>Shows if recordings are in progress or completed</li>
      <li>Provides links to video, audio, and transcript downloads</li>
      <li>Displays metadata like duration and participants</li>
    </ul>
  </td>
</tr>
<tr>
  <td width="25%" align="center">
    <h4>🤖<br>Create Recording Bot</h4>
  </td>
  <td>
    Creates and deploys a new bot to record a Google Meet session:
    <ul>
      <li>Accepts Google Meet URLs in any format</li>
      <li>Automatically joins meetings using specified credentials</li>
      <li>Creates a dedicated recorder ID for tracking</li>
    </ul>
  </td>
</tr>
<tr>
  <td width="25%" align="center">
    <h4>📧<br>Send Email Content</h4>
  </td>
  <td>
    Sends meeting summaries and recordings via email:
    <ul>
      <li>Sends transcript summaries to meeting participants</li>
      <li>Attaches or links to recording files</li>
      <li>Supports customized email templates</li>
    </ul>
  </td>
</tr>
<tr>
  <td width="25%" align="center">
    <h4>📅<br>Get Calendar Events</h4>
  </td>
  <td>
    Connects with your Google Calendar:
    <ul>
      <li>Fetches upcoming and past calendar events</li>
      <li>Links calendar events to meeting recordings</li>
      <li>Provides scheduling information for the agent</li>
    </ul>
  </td>
</tr>
</table>

## 🔍 Usage

### Basic Commands

Check all your recorded meetings (you will get 404 error here on the first run, because you didn't record anything yet)

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

### Thread Management

Continue the previous conversation (default behavior):

```bash
# This will use the existing thread_id.txt file
python app.py "what's the status of my recordings?"
```

Start a completely new conversation thread:

```bash
# This will ask for confirmation if an existing thread is found
python app.py --new-thread "please record a new meeting"
```

### Example Workflow

1. **First run** - Record a meeting:
   ```bash
   python app.py "record meet.google.com/abc-defg-hij"
   # This creates a new thread and stores its ID
   ```

2. **Later run** - Check recording status:
   ```bash
   python app.py "how's my recording going?"
   # This continues the same thread, so the agent remembers the meeting
   ```

3. **Optional reset** - Start fresh:
   ```bash
   python app.py --new-thread "let's start tracking a different set of meetings"
   # This creates a new thread with no memory of previous meetings
   ```

The agent will automatically:
- Create a new thread if none exists
- Continue with the existing thread when available
- Ask for confirmation before overriding an existing thread

## 💾 Thread-Based Memory System

The agent uses xpander.ai's thread-based memory system instead of storing meeting data locally. Here's how it works:

### How Threads Work
- Each **thread** represents an ongoing conversation about meetings
- The agent remembers all context within a thread, including:
  - Meeting URLs you've shared
  - Recording bot IDs and statuses
  - Previous requests and interactions

### Thread Management
The application handles threads intelligently:

1. **First Run**: Creates a new thread automatically and saves its ID to `thread_id.txt`
2. **Subsequent Runs**: Loads the existing thread ID to continue the same conversation
3. **With `--new-thread` Flag**: 
   - If a thread already exists, asks for confirmation before replacing it
   - If confirmed, creates a fresh thread with no previous context

This approach provides several benefits:
- **Persistent Memory**: The agent remembers all previous meetings across sessions
- **Seamless Continuity**: Pick up conversations exactly where you left off
- **Simple Storage**: Only the thread ID needs to be stored locally
- **Clean Reset Option**: Start fresh when needed with the `--new-thread` flag

For example, if you record a meeting in one session, you can ask about its status in a later session, and the agent will remember all the details as long as you're using the same thread.

## 📊 Example Output

When you run the agent asking about calendar events:

```bash
python app.py "what's on my calendar"
```

It responds with:

```
Here are the events on your calendar and the status of the recording bots:

### Calendar Events:
1. **Onboarding to xpander**
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

![xpander Dashboard](static/images/screenshots/2025-04-12-12-27-31.png)

## 👨‍💻 Built With xpander.ai

[xpander.ai](https://xpander.ai) is an AI Agent platform that lets developers build, test, and deploy AI agents quickly. It provides:

- **State Management**: Handles complex agent states so you don't have to
- **Provider Independence**: Works with OpenAI, Anthropic, Gemini, and more
- **Tool Integration**: Easy calendar, meeting, and custom tool integration

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

Questions? Reach out to us at [support@xpander.ai](mailto:support@xpander.ai)
