system_prompt_graph_decision = '''
return your input tools with the correct args
'''

retrieval_agent_prompt = '''
As a retrieval agent, your task is to get all the information about the company: '{company}' by using all the input resources: Perplexity, linkedin and Notion.
you need to return all the tools requests in one request.
here are the required tools:
1. From Linkedin Company Page you expected to find their company page by domain {company_domain} and return all the metadata information includes the company logo.
2. From Linkedin Posts you need also to find all the latest posts that related to the company and return them.
3. From Perplexity you expected to get all the news information about this company: '{company}' that show what this company doing in the last 3 months.
4. From Tavily return information about '{company}' from their domain website. in the include domains set only the company domain in this list: [{company_domain}] and make sure you return the company's logo.
5. From Notion you expected to get all the information blocks from the page id: '14629ef8-30b3-804b-8510-c1fdd3fef9fa'. the page is related to 'xpander.ai' company.
return all the 5 tool requests!
'''
collaborate_agent_prompt = '''
As a collaborate agent, your task is to get all the following information about the company: '{company}' and also the information about the company called 'xpander.ai' and write the collaboration paragraph based on the following template how Xpander.ai is related to {company} and can help this company to improve their business by using Xpander.ai's AI agents.
The title of this paragraph is 'EMPOWERING YOUR BUSINESS WITH BETTER AI AGENTS' and you need to write the paragraph in the same style of the template.

rules:
1. you must related in your answer to all input information that you got about '{company}' and the data about xpander.ai.
2. this paragraph must be human readable with maximum 4 sentences.
3. the output text will insert into HTML page, for using link you must use html link format: <a href="URL">Link Text</a>.
4. you must convince the {company}'s employee why he/she should use xpander.ai.
5. do not return generic reasons, use the input information to be convincing.
6. return actual links about {company}'s that show news and posts that related to this company to be more convincing.
7. Do not add the title 'EMPOWERING YOUR BUSINESS WITH BETTER AI AGENTS' to your answer! it's already in the template.

here all the information about the company called 'xpander.ai':
{xpander_ai_info}
here all the information about the company: '{company}':
{company_info}

Began!
'''


use_cases_agent_prompt = '''
As a use cases writer agent, your task is to get all the following information about the company: '{company}' and also the information about the company called 'xpander.ai' and write 2 use cases how the company '{company}' can use xpander.ai to create an AI agent that can help them to improve their business.
based your uses cases on the linkedin posts, Perplexity results, Tavily about '{company}' and Notion information about xpander.ai.
The title of this paragraph is 'AI AGENTS OPPORTUNITIES FOR {company}' and you need to write the 2 use cases in the same style of the template.

return the uses cases in a bullet lists of html format format:

expected output:
```html
<ul>
    <li style="margin: 0; padding: 0;><strong>[Use Case 1 title]</strong>:<br>use case 1 description</li>
    <li style="margin: 0; padding: 0;><strong>[Use Case 2 title]</strong>:<br>use case 2 description</li>
</ul>
```

rules:
1. the use cases must related to the latest posts, linkedin company metadata, Tavily data and perplexity and what xpander probational doing.
2. it should be short and clear with maximum of 2 sentences and informative title.
3. it should be real use cases that this company faced with.
4. it must start with human readable title with minimum words.
5. the output text will insert into HTML page, for using link you must use html link format: <a href="URL">Link Text</a>.
6. return actual links about {company}'s that show news and posts that related to this company to be more convincing.
7. Do not add the title 'AI AGENTS OPPORTUNITIES FOR {company}' to your answer! it's already in the template.

here all the information about the company called 'xpander.ai':
{xpander_ai_info}
here all the information about the company: '{company}':
{company_info}

Began!
'''


email_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Thank You from xpander.ai</title>
    <style>
        /* Basic styling to make the email look appealing */
        body {{
            font-family: Arial, sans-serif;
            background-color: #f7f7f7;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            background-color: #fff;
            margin: auto;
            padding: 30px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #640b86;
            text-align: center;
        }}
        p {{
            line-height: 1.6;
        }}
        a {{
            color: #640b86;
            text-decoration: none;
        }}
        .button {{
            display: inline-block;
            background-color: #640b86;
            color: #000;
            font-weight: bold;
            padding: 12px 25px;
            margin-top: 20px;
            text-align: center;
            text-decoration: none;
            border-radius: 5px;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #aaa;
        }}
        @media (max-width: 600px) {{
            .container {{
                padding: 15px;
            }}
            .button {{
                width: 100%;
                padding: 15px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Beautiful Headline -->
        <h1>Welcome to xpander.ai!</h1>

        <!-- Thank You Message -->
        <p>Thank you for visiting the <a href="https://xpander.ai">xpander.ai</a> booth!</p>
        <p>We are excited to share with you the generated summary for <strong>{company_name}</strong>. Please click the button below to view your personalized summary.</p>

        <!-- Link to the Generated Summary -->
        <a href="{link}" class="button">View Your Summary</a>


        <!-- Footer -->
        <div class="footer">
            &copy; 2023 xpander.ai. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

basic_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Basic HTML Page</title>
</head>
<body>
    <h1>Welcome to My Website</h1>
    <p>This is a simple HTML page.</p>
</body>
</html>
"""


send_email_prompt = "please send an email to test@xpander.ai with the basic html {basic_html}"
