import re
from typing import Any

from agents.base_agent import BaseAgent
from agents.memory_messaging import MemoryMessaging

DEFAULT_SYSTEM_MESSAGE = """You are an agent that breaks down user queries into sub-task plans, with each sub-task corresponding to a specific tool call. Your goal is to ensure that each part of the user's query is addressed by an appropriate tool or sequence of tool interactions."""

DEFAULT_TASK_MESSAGE = """
Your task: 
Break down the user's query into sub-task plans, with each sub-task corresponding to a specific tool call. Ensure the plan is detailed and addresses each part of the query using the appropriate tool interactions.

This is the input template:
User query: [the query a user wants help with related to the API].
Plan step 1: [the first step of your plan for how to solve the query].
Tool Name: [the tool name you want for this sub task].
Parser Response: [the result of executing the first step of your plan, including the specific API call made].
Plan step 2: [based on the API response, the second step of your plan for how to solve the query. If the last step result is not what you want, you can output "Continue" to let the API selector select another API to fulfill the plan. Pay attention to the specific API called in the last step API response. If an improper API is called, the response may be wrong, and you should give a new plan].
Tool Name: [the tool name you want for this sub task].
Parser Response: [the result of executing the second step of your plan].
... (this Plan step n and API response can repeat N times).


this is the expected output template:
if the query has not been fulfilled:
Plan step (i+1): [the next step of your plan for how to solve the query].

otherwise:
Thought: [I am finished executing the plan and have the information the user asked for or the data the user asked to create].
Final Answer: [the final output from executing the plan].

These are the strict rules:
1. Always provide your plan in natural language, ensuring it is closely related to the input tools.
2. Be specific in the plan and explain what should be the results of this step after parsing the API response. 
3. Each subtask should be related to user query. always stick to the user query and do not make up new tasks with non relevant data.
4. If you believe you have the final answer or the user's query has been fulfilled (only after at least one 'Parser Response'), output the answer immediately with the prefix: 'Final Answer:'.
5. User's query can't be fulfilled without at least one 'Parser Response'. You can't fulfill task without at least one API calling and response.
6. If the query has not been fulfilled, explain how to fix the last step and continue to output your plan.
7. Return only the next Plan step (i+1) you generated and do not mention all the steps list until now. you'll get the conversation history with User query, Plan steps [1,...,i-1] and API responses after parsing, you will use it to generate the next step.
8. If you've got an iterative task and no beach endpoint can fulfill the task, split the big task into multiple sub-tasks. For example, if you need to add 5 users, but there is only one endpoint to add one user per call, then you need to split the task into 5 plans with each iteration.
9. If the the API request failed, return how you recommend to handle with this error in the next plan step so your step plan will success.
10. If the tool execution failed, return the error message and the tool name with the solution to fix the error, so the tool selector can select the right tool with the correct parameters.
11. Make sure you explain clear where to put the name of the object you are referring to, for example: "Add the song [song name] by [artist name] to my workout playlist on Spotify."
12. you must be accurate with the required input parameters and specified how they should be in the output request.

Here are examples:

Example 1:
Input:
User query: Add the song "Shape of You" by Ed Sheeran to my workout playlist on Spotify.
Plan step 1: Search for the song "Shape of You" by Ed Sheeran on Spotify and extract it song ID.
Tool Name: GetAllSongs
Parser Response: Result of the search, including song ID.
Output:
Plan step 2: Add the song with ID: [song ID] to the workout playlist.

Example 2:
Input:
User query: Find the top 5 movies directed by Christopher Nolan on TMDB.
Plan step 1: Search for movies directed by Christopher Nolan on TMDB and sort the response list of movies by rating and select the top 5. return tha name, id and rating for each movie.
Tool Name: GetAllMovies
Parser Response:[{  "name": "The Dark Knight",  "id": 155,  "published": 2008,  "rating": 9.0},{  "name": "Inception",  "id": 27205,  "published": 2010,  "rating": 8.8},{  "name": "Interstellar",  "id": 157336,  "published": 2014,  "rating": 8.6},{  "name": "Dunkirk",  "id": 374720,  "published": 2017,  "rating": 7.9},{  "name": "Memento",  "id": 77,  "published": 2000,  "rating": 8.4},{  "name": "The Prestige",  "id": 1124,  "published": 2006,  "rating": 8.5},{  "name": "Batman Begins",  "id": 272,  "published": 2005,  "rating": 8.2},{  "name": "The Dark Knight Rises",  "id": 49026,  "published": 2012,  "rating": 8.4}].
Output:
Thought: I have the list of top 5 movies directed by Christopher Nolan.
Final Answer: Here are the top 5 movies directed by Christopher Nolan: [List of movies].

Example 3:
Input:
User query: Send a LinkedIn connection request to John Doe.
Output:
Plan step 1: Search for John Doe on LinkedIn.
Tool Name: LinkedInSearch

Example 4:
Input:
User query: Post a message to 'Bob' on Slack saying "Hi 👋".
Plan step 1: Find the ID of 'Bob' on Slack and return it as Bob: user_id = [user_id].
Tool Name: GetAllUsers
Parser Response: ID of the user 'Bob': 124252.
Plan step 2: Post the message "Hi 👋" using the user ID: 124252. return that the 'message has been posted'.
Tool Name: PostMessage
Parser Response: message has been posted.
Output:
Thought: The message has been posted to 'Bob'.
Final Answer: The message "Hi 👋" has been posted to user called 'Bob' on Slack.

Begin!

"""


class PlannerAgent(BaseAgent):
    def __init__(self, handler, tools: list,
                 task_message: str = DEFAULT_TASK_MESSAGE,
                 system_message: str = DEFAULT_SYSTEM_MESSAGE, finish_message: str = "Final Answer",
                 agent_log_color: str = "GREEN"):
        agent_type = "PlannerAgent"
        super().__init__(agent_type=agent_type, handler=handler, tools=tools, tool_choice="none",
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.finish_message = finish_message
        self.is_finished = False
        self.step_number = 1

    def run_post_processing(self, response: Any, memory: MemoryMessaging = None, extract_data: dict = None):
        if re.search(self.finish_message, response):
            self.is_finished = True 
            memory.add_message(response)
        self.logger.info(response)
        return response

    def finished(self) -> bool:
        return self.is_finished
