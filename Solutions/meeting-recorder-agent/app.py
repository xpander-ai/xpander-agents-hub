from dotenv import load_dotenv
import os, argparse, time, sys
from meeting_agent import MeetingAgent

# Setup
load_dotenv()
THREAD_ID_FILE = "thread_id.txt"

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Meeting Recorder Agent')
parser.add_argument('prompt', nargs='?', help='Prompt for the agent (optional)', default="")
parser.add_argument('--new-thread', action='store_true', help='Start a new conversation thread (will ask for confirmation if a thread already exists)')
args = parser.parse_args()

# Check for required environment variables
REQUIRED_VARS = ["OPENAI_API_KEY", "XPANDER_API_KEY", "XPANDER_AGENT_ID"]
missing_vars = [var for var in REQUIRED_VARS if not os.environ.get(var)]
if missing_vars:
    print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

def load_thread_id():
    """Load the thread ID from file if available"""
    try:
        with open(THREAD_ID_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_thread_id(thread_id):
    """Save the thread ID to file"""
    with open(THREAD_ID_FILE, 'w') as f:
        f.write(thread_id)

def confirm_thread_override():
    """Ask user to confirm overriding the existing thread"""
    while True:
        response = input("An existing conversation thread was found. Override it with a new one? (y/n): ").lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer with 'y' or 'n'")

def main():
    """Main entry point"""
    # Initialize agent
    meeting_agent = MeetingAgent(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        xpander_api_key=os.environ["XPANDER_API_KEY"],
        agent_id=os.environ["XPANDER_AGENT_ID"]
    )
    
    # Check if thread exists
    thread_id = load_thread_id()
    create_new_thread = False
    
    # Determine if we should create a new thread
    if args.new_thread and thread_id:
        # User requested new thread and one exists - confirm override
        if confirm_thread_override():
            thread_id = None
            create_new_thread = True
            print("Starting a new conversation thread")
        else:
            print(f"Continuing with existing thread: {thread_id}")
    elif args.new_thread:
        # User requested new thread and none exists
        create_new_thread = True
        print("Starting a new conversation thread")
    elif thread_id:
        # Thread exists and no override requested
        print(f"Using existing thread ID: {thread_id}")
    else:
        # No thread exists and none requested - create a new one
        create_new_thread = True
        print("No existing thread found. Starting a new conversation thread")
    
    while True:
        try:
            # Run the agent with appropriate thread ID
            result_text, new_thread_id = meeting_agent.run(args.prompt, thread_id=thread_id)
            
            # Save the thread ID for future use if it's new or changed
            if new_thread_id and (not thread_id or thread_id != new_thread_id or create_new_thread):
                thread_id = new_thread_id
                save_thread_id(thread_id)
                print(f"Saved thread ID: {thread_id}")
                # Reset create_new_thread flag after first run
                create_new_thread = False
            
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