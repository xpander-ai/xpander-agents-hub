from dotenv import load_dotenv
import os, argparse, time, sys
from recordings import RecordingsManager
from meeting_agent import MeetingAgent

# Setup
load_dotenv()
RECORDINGS_FILE = "recording_ids.json"

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Meeting Recorder Agent')
parser.add_argument('prompt', nargs='?', help='Prompt for the agent (optional)', default="")
args = parser.parse_args()

# Check for required environment variables
REQUIRED_VARS = ["OPENAI_API_KEY", "XPANDER_API_KEY", "XPANDER_AGENT_ID"]
missing_vars = [var for var in REQUIRED_VARS if not os.environ.get(var)]
if missing_vars:
    print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

def main():
    """Main entry point"""
    # Initialize components
    recordings_manager = RecordingsManager(RECORDINGS_FILE)
    meeting_agent = MeetingAgent(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        xpander_api_key=os.environ["XPANDER_API_KEY"],
        agent_id=os.environ["XPANDER_AGENT_ID"]
    )
    
    while True:
        try:
            # If there's a prompt with a URL, add it to recordings DB immediately
            if args.prompt:
                recordings_manager.add_meeting_from_prompt(args.prompt)

            # Run the agent
            meeting_agent.run(args.prompt, recordings_manager)
            
            # Wait 5 minutes between checks
            print("\nWaiting 5 minutes before next check...")
            time.sleep(300)
            
        except KeyboardInterrupt:
            print("\nProcess interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(30)  # Wait 30 seconds before retry

if __name__ == "__main__":
    main()