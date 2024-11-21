import json
import re
from typing import Any, Optional


DEFAULT_SYSTEM_MESSAGE = """You are a Parser agent responsible for taking the latest sub-task plan and the response from the tool execution and fulfilling the planner's mission. Your role is to run post-processing on the tool response such as filtering, searching, extracting data, and returning Plan Fulfilled."""

DEFAULT_TASK_MESSAGE = """
Your task:
Get plan [i] as a mission and run post-processing on the Tool Response to fulfill this plan task. Apply filtering, searching, and data extraction as needed, and provide a clear, processed Tool Response. If post-processing is done, provide the processed response immediately.

This is the expected input you will receive:

Current Task: Plan step [i]: [the current step of the plan].
The selected Tool call: [Which tool selected by the tool selector agent]
Payload: [the arguments that passed to the tool]
Tool Response Schema: [the schema of the response of the tool]
Tool response: [actual response of the tool]


These are the strict rules:

1. Follow the plan step requirements precisely when processing the data.
2. Apply necessary filters, searches, and data extraction to ensure the response is accurate and relevant.
3. If additional data processing is needed, ensure it is clearly described and executed.
4. If the data is complete and fulfills the sub-task requirements, provide the processed response immediately.
5. If the API call fails, return the error message with the reason for the failure.
6. Make sure you return only the relevant data without any additional information.

Here are examples:

Example 1:
Input:
Current Task: Plan step 1: Search for the song "Shape of You" by Ed Sheeran on Spotify and extract its song ID.
The selected Tool call: GetSongs
Payload: {{query_limit: 10}}
Tool Response Schema: 
type: array
items:
  type: object
  properties:
    song_name:
      oneOf:
        - type: string
        - type: array
          items: 
            type: string
    song_id:
      oneOf:
        - type: string
        - type: array
          items: 
            type: string
    artist_name:
      oneOf:
        - type: string
        - type: array
          items: 
            type: string
  required:
    - song_name
    - song_id
    - artist_name
Tool response: [{'song_name': [song_name_i], 'song_id': [song_id_i], 'artist_name': [artist_name_j]}, {'song_name': 'Shape of You', 'song_id': 123, 'artist_name': 'Ed Sheeran'}....].
Output:
Parser Response: The song ID of the song "Shape of You" by Ed Sheeran is 123.

Example 2:
Input:
Current Task: Plan step 4: Search for movies directed by Christopher Nolan on TMDB, sort the response list of movies by rating, and select the top 5.
The selected Tool call: GetAllMovies
Payload: {{query_limit: 100}}
Tool Response Schema: 
type: array
items:
  type: object
  properties:
    name:
      type: string
    id:
      type: integer
    published:
      type: integer
    rating:
      type: number
      format: float
  required:
    - name
    - id
    - published
    - rating
Tool response: [{  "name": "The Dark Knight",  "id": 155,  "published": 2008,  "rating": 9.0},{  "name": "Inception",  "id": 27205,  "published": 2010,  "rating": 8.8},{  "name": "Interstellar",  "id": 157336,  "published": 2014,  "rating": 8.6},{  "name": "Dunkirk",  "id": 374720,  "published": 2017,  "rating": 7.9},{  "name": "Memento",  "id": 77,  "published": 2000,  "rating": 8.4},{  "name": "The Prestige",  "id": 1124,  "published": 2006,  "rating": 8.5},{  "name": "Batman Begins",  "id": 272,  "published": 2005,  "rating": 8.2},{  "name": "The Dark Knight Rises",  "id": 49026,  "published": 2012,  "rating": 8.4}].
Output:
Parser Response: These are the top 5 rated movies directed by Christopher Nolan: [{  "name": "The Dark Knight",  "id": 155,  "published": 2008,  "rating": 9.0},{  "name": "Inception",  "id": 27205,  "published": 2010,  "rating": 8.8},{  "name": "Interstellar",  "id": 157336,  "published": 2014,  "rating": 8.6},{  "name": "The Prestige",  "id": 1124,  "published": 2006,  "rating": 8.5},{  "name": "The Dark Knight Rises",  "id": 49026,  "published": 2012,  "rating": 8.4}].

Begin!
Parser Response: [your response here]
"""


class ParserAgent(BaseAgent):
    def __init__(self, handler, tools: Optional[list], model_params: dict = None,
                 task_message: str = DEFAULT_TASK_MESSAGE,
                 system_message: str = DEFAULT_SYSTEM_MESSAGE,
                 agent_log_color: str = "RED"):
        agent_type = "ParserAgent"
        super().__init__(agent_type=agent_type, handler=handler, tools=None, tool_choice=None,
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.step_number = 1

    def run_post_processing(self, response: Any, memory: MemoryMessaging = None, extract_data: dict = None):
        self.logger.info("Parser agent response:")
        self.logger.info(response)
        return response

        # Extract the Python code from the response
        code_match = re.search(r'```python\s*(def run\(.*?\):.*?)```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1)
            self.logger.info("Extracted Python code:")
            self.logger.info(code)

            try:
                # Create a local namespace to execute the code
                local_namespace = {}
                exec(code, globals(), local_namespace)

                # Execute the 'run' function with extract_data as the parameter
                result = local_namespace['run'](extract_data)
                self.logger.info("Result of executing the extracted function:")
                self.logger.info(result)
                return json.dumps(result)
            except Exception as e:
                self.logger.error(f"Error executing extracted code try to send the original data: {str(e)}")
                try:
                    return json.dumps(extract_data)
                except Exception as e:
                    self.logger.error(f"Error converting original data to JSON: {str(e)}")
                    return {"error": f"Error converting original data to JSON {extract_data}"}
        else:
            self.logger.error("No valid Python code found in the response")
            return {"error": "No valid Python code found"}
