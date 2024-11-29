import asyncio
import streamlit as st
import logging
from run_company_to_mail import run_company_query
from loguru import logger

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def main():
    # Add logo
    with open("xpanderLogo.svg", "r") as f:
        svg = f.read()
    
    st.markdown(f"""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            {svg}</div>
    """, unsafe_allow_html=True)
    
    st.title("Company Analysis Tool")
    
    # Create a container for the form
    with st.form("analysis_form"):
        company = st.text_input(
            "Company Name",
            placeholder="Enter company name"
        )
        
        xpander_email = st.text_input(
            "Xpander Employee Email",
            placeholder="employee@xpander.ai"
        )
        
        email = st.text_input(
            "Email (optional)", 
            placeholder="user@example.com"
        )
        
        client_name = st.text_input(
            "Client Name (optional)",
            placeholder="John Doe"
        )
        
        submit_button = st.form_submit_button("Analyze Company")

    # Create containers for status and logs
    status_container = st.empty()
    log_container = st.empty()
    
    if submit_button and company:
        status_container.info("Starting analysis...")
        
        try:
            # Custom handler to display only specific logs in Streamlit
            class StreamlitHandler(logging.Handler):
                def __init__(self, container):
                    super().__init__()
                    self.container = container
                    self.log_messages = []

                def emit(self, record):
                    # Only display logs that start with specific prefixes
                    msg = self.format(record)
                    if any(msg.startswith(prefix) for prefix in [
                        "Topic:",
                        "Starting",
                        "Completed",
                        "Selected",
                        "Processing"
                    ]):
                        self.log_messages.append(msg)
                        # Join all messages with newlines and update the container
                        self.container.info("\n".join(self.log_messages))
            
            # Add our custom handler
            streamlit_handler = StreamlitHandler(log_container)
            logger.addHandler(streamlit_handler)
            
            # Run the analysis
            qr_code_base64 = await run_company_query(
                company=company,
                xpander_employee_email=xpander_email if xpander_email else None,
                email=email if email else None,
                client_name=client_name if client_name else None
            )
            
            # Remove our custom handler
            logger.removeHandler(streamlit_handler)
            
            status_container.success("Analysis completed successfully!")
            
            # Display QR code
            if qr_code_base64:
                st.image(qr_code_base64, caption="Scan this QR code to view the analysis")
            
        except Exception as e:
            status_container.error(f"An error occurred: {str(e)}")
            
    elif submit_button:
        st.warning("Please enter a company name")

if __name__ == "__main__":
    asyncio.run(main())