import json
import re
import uuid

class RecordingsManager:
    """Utility class for managing recording IDs and URLs"""
    
    def __init__(self, recordings_file="recording_ids.json"):
        self.recordings_file = recordings_file
        # Simple regex patterns for common URL formats
        self.meet_url_pattern = re.compile(r'(meet\.google\.com/[\w\-]+)')
        self.url_pattern = re.compile(r'(https?://[^\s\'\"]+)')
        # UUID pattern for identifying recording IDs
        self.uuid_pattern = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')
        
    def load(self):
        """Load recordings data from the JSON file"""
        try:
            with open(self.recordings_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save(self, recordings):
        """Save recordings data to the JSON file"""
        with open(self.recordings_file, 'w') as f:
            json.dump(recordings, f, indent=2)
    
    def extract_urls(self, text):
        """Extract URLs from text, prioritizing Google Meet URLs"""
        # First check for Google Meet URLs
        meet_urls = re.findall(self.meet_url_pattern, text)
        if meet_urls:
            # Ensure they have https:// prefix
            return [f"https://{url}" if not url.startswith('http') else url for url in meet_urls]
        
        # Otherwise look for any URLs
        return re.findall(self.url_pattern, text)
    
    def extract_ids(self, text):
        """Extract recording IDs from text"""
        return list(set(re.findall(self.uuid_pattern, text)))
    
    def normalize_url(self, url):
        """Normalize a URL to a standard format for use as a key"""
        # Extract the meet.google.com part if it exists
        meet_match = re.search(self.meet_url_pattern, url)
        if meet_match:
            url = meet_match.group(0)
            # Ensure it has https:// prefix
            if not url.startswith('http'):
                url = f"https://{url}"
        return url
    
    def add_meeting_from_prompt(self, prompt):
        """Extract and add a meeting URL directly from the user's prompt"""
        if not prompt:
            return None
            
        # Look for Google Meet URLs in the prompt
        urls = self.extract_urls(prompt)
        if not urls:
            return None
        
        # Use the meeting URL as the key    
        meeting_url = self.normalize_url(urls[0])
        
        # Add to recordings with temporary recorder ID if needed
        recordings = self.load()
        
        # Check if we already have this URL
        for record_id, record in recordings.items():
            if record.get("url") == meeting_url:
                print(f"Meeting URL already exists with ID: {record_id}")
                return record_id
        
        # If not found, create a new temporary ID
        temp_id = str(uuid.uuid4())
        recordings[temp_id] = {
            "url": meeting_url,
            "temporary": True  # Mark as temporary so we can update it later
        }
        self.save(recordings)
        
        print(f"Added new meeting from prompt: {temp_id} with URL: {meeting_url}")
        return temp_id
    
    def process_results(self, result_text):
        """Process results to extract and save new recording IDs or update existing ones"""
        recordings = self.load()
        
        # Extract recorder IDs from the result text
        new_ids = []
        recorder_ids = self.extract_ids(result_text)
        
        # Extract URLs from the result text
        result_urls = self.extract_urls(result_text)
        
        # Initialize found_temp flag outside the loop to avoid the error
        found_temp = False
        
        # Process each ID found
        for recorder_id in recorder_ids:
            # Try to find the URL specifically associated with this ID
            url = self._find_url_for_id(result_text, recorder_id)
            
            if url:
                url = self.normalize_url(url)
                
                # Check if this URL already exists with a temporary ID
                for existing_id, details in list(recordings.items()):
                    if details.get("url") == url and details.get("temporary", False):
                        # Update the temporary entry with the real recorder ID
                        recordings[recorder_id] = {"url": url}
                        del recordings[existing_id]
                        found_temp = True
                        print(f"Updated temporary ID {existing_id} to recorder ID: {recorder_id} for URL: {url}")
                        break
                
                if not found_temp:
                    # Check if we already have this recorder ID
                    if recorder_id not in recordings:
                        recordings[recorder_id] = {"url": url}
                        new_ids.append(recorder_id)
                        print(f"Added new recording ID: {recorder_id} with URL: {url}")
        
        if new_ids or found_temp:
            self.save(recordings)
        
        return new_ids
    
    def _find_url_for_id(self, text, recording_id):
        """Find a URL associated with a recording ID (simplified)"""
        # Look for URLs in the context after the ID
        id_context = text.split(recording_id, 1)
        if len(id_context) > 1:
            context_after = id_context[1][:200]  # Look at up to 200 chars after the ID
            
            # First try to find a Google Meet URL
            meets_after = re.findall(self.meet_url_pattern, context_after)
            if meets_after:
                url = meets_after[0]
                return f"https://{url}" if not url.startswith('http') else url
            
            # Then try any URL
            urls_after = re.findall(self.url_pattern, context_after)
            if urls_after:
                # Filter out Xpander asset links
                for url in urls_after:
                    if 'xpander.ai' not in url and 'links.xpander' not in url:
                        return url
        
        # If no specific URL found for this ID, try general URLs in the text
        meets = re.findall(self.meet_url_pattern, text)
        if meets:
            url = meets[0]
            return f"https://{url}" if not url.startswith('http') else url
            
        # As a last resort, return any URL that isn't from Xpander
        all_urls = re.findall(self.url_pattern, text)
        for url in all_urls:
            if 'xpander.ai' not in url and 'links.xpander' not in url:
                return url
        
        return ""
    
    def get_recordings_info(self):
        """Get formatted info about all recordings for display"""
        recordings = self.load()
        if not recordings:
            return ""
            
        lines = []
        for id, details in recordings.items():
            # Skip displaying temporary flag in the output
            url_info = f" (URL: {details.get('url', '')})" if details.get('url') else ""
            lines.append(f"- {id}{url_info}")
            
        return "\n".join(lines) 