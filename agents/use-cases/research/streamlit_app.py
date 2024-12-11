import streamlit as st
import time
from research_by_user_query import run_research_agent
import logging
from datetime import datetime
from PIL import Image
import os
import base64
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ICON = os.path.join(BASE_DIR, "xpander_logo.jpeg")
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_session_state():
    """Initialize session state variables"""
    if 'research_history' not in st.session_state:
        st.session_state.research_history = []
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False

def display_research_history():
    """Display the history of research queries and results"""
    if st.session_state.research_history:
        st.subheader("Research History")
        for item in st.session_state.research_history:
            with st.expander(f"Research: {item['query']} - {item['timestamp']}"):
                st.markdown(item['result'])
                if 'pdf_link' in item:
                    st.markdown(f"[View Full Report]({item['pdf_link']})")

def update_progress_for_tool(tool_name: str, status_text, progress_bar):
    """Update progress based on the current tool being used"""
    tool_progress = {
        "tavily-insights-fetchInsightsFromTavilyAI": ("🌐 Searching web sources...", 30),
        "ArxivResearchPaperQueryRetrieveArticlesBySearchOrId": ("📚 Analyzing academic papers...", 50),
        "PerplexityChatCompletionCreateAIGeneratedResponse": ("🤖 Processing with AI...", 70),
        "LinkedInPostManagementSearchPostsByCriteria": ("👥 Gathering expert insights...", 80),
        "pdf-operations-convertMarkdownToPDF": ("📝 Creating PDF report...", 90)
    }
    
    if tool_name in tool_progress:
        message, progress = tool_progress[tool_name]
        status_text.text(message)
        progress_bar.progress(progress)
        time.sleep(0.5)

def run_research_with_progress(query: str, progress_bar, status_text):
    """Run research with synchronized progress updates"""
    try:
        # Initial research setup
        status_text.text("🤔 Planning research strategy...")
        progress_bar.progress(10)
        time.sleep(1)
        
        # Create progress callback
        def progress_callback(tool_name):
            update_progress_for_tool(tool_name, status_text, progress_bar)
        
        # Run research with progress updates
        result = run_research_agent(query, progress_callback=progress_callback)
        
        # Complete
        status_text.text("✅ Research completed!")
        progress_bar.progress(100)
        return result
        
    except Exception as e:
        status_text.text("❌ Error occurred")
        raise e
    
def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def main():
    
    # Initialize session state first
    initialize_session_state()
    
    logo_im = Image.open(APP_ICON)
    logo_im = logo_im.resize((32, 32), Image.Resampling.LANCZOS)
    st.set_page_config(
        page_title="Xpander AI Research Agent",
        page_icon=logo_im,
        layout="wide"
    )
    
    # Custom CSS for header layout
    st.markdown("""
        <style>
        .header-container {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
        }
        .logo-img {
            width: 32px;
            height: 32px;
        }
        .title-text {
            color: white;
            font-size: 36px;
            font-weight: bold;
            margin: 0;
        }
        .subtitle-text {
            color: #888888;
            font-size: 16px;
            margin-top: 0;
            margin-bottom: 20px;
        }
        
        </style>
    """, unsafe_allow_html=True)

    # Create header with logo and title
    st.markdown(
        f"""
        <div class="header-container">
            <img class="logo-img" src="data:image/png;base64,{get_base64_encoded_image(APP_ICON)}">
            <h1 class="title-text">Xpander AI Research Agent</h1>
        </div>
        <p class="subtitle-text">Your intelligent research companion powered by AI. Get comprehensive PDF reports on any topic from multiple sources.</p>
        """,
        unsafe_allow_html=True
    )
    # Custom CSS to ensure purple accents and dark theme
    st.markdown("""
        <style>
        /* Button colors */
        .stButton>button {
            background-color: #7b08d6 !important;
            color: white;
            border: none;
        }
        .stButton>button:hover {
            background-color: #7b08d6 !important;
            border: none;
        }
        
        /* Progress bar color */
        .stProgress > div > div > div > div {
            background-color: #7b08d6 !important;
        }
        
        /* Spinner color */
        .stSpinner > div > div > div {
            border-top-color: #7b08d6 !important;
        }
        
        /* Success message with purple */
        .stSuccess {
            background-color: rgba(123, 8, 214, 0.2) !important;
            border: 1px solid #7b08d6;
        }
        </style>
    """, unsafe_allow_html=True)


    # Create containers for different sections
    input_container = st.container()
    progress_container = st.container()
    results_container = st.container()
    
    # Input section with query and button
    with input_container:
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input(
                "## What would you like to research?",
                placeholder="Enter your research topic...",
                disabled=st.session_state.is_processing
            )
        with col2:
            st.write("  ")
            start_button = st.button(
                "Start Research",
                disabled=st.session_state.is_processing or not query,
                type="primary"
            )

    # Progress section
    with progress_container:
        if start_button and query:
            st.session_state.is_processing = True
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Start with planning phase
                status_text.text("🤔 Planning research strategy...")
                progress_bar.progress(10)
                time.sleep(1)  # Short delay for visual feedback

                # Run the research with progress updates
                result = run_research_with_progress(query, progress_bar, status_text)
                
                st.session_state.research_history.append({
                    'query': query,
                    'result': result,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'pdf_link': result.split("Final Answer: ")[-1].strip() if "http" in result and ".pdf" in result else None
                })
                
                # Display results after completion
                with results_container:
                    st.success("Research completed successfully!")
                    st.markdown("### Results")
                    st.markdown("Your report is ready to download:")
                    st.markdown(result)
                
            except Exception as e:
                status_text.text("❌ Error occurred")
                st.error(f"An error occurred: {str(e)}")
                logger.error(f"Research error: {e}")
            finally:
                st.session_state.is_processing = False

    # Display history
    if st.session_state.research_history:
        st.markdown("---")
        st.markdown("### Research History")
        for item in reversed(st.session_state.research_history):
            with st.expander(f"{item['query']} - {item['timestamp']}"):
                st.markdown(item['result'])
                if 'pdf_link' in item and item['pdf_link']:
                    st.markdown(f"[View Full Report]({item['pdf_link']})")

if __name__ == "__main__":
    main() 