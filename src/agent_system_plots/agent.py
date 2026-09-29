import sys
import io
import os
from openai import OpenAI
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv() 

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", 'http://127.0.0.1:11434/v1')
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable was not found")

client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY
)

SYSTEM_PROMPT_WITH_FILE = """
You are an expert Python Data Visualization Engineer. 
Your task is to write Python code to create an interactive Plotly Express chart based on the user's request.

CONTEXT:
A Pandas DataFrame named `df` is ALREADY loaded in memory. You are provided with its metadata and a preview.

STRICT RULES:
1. USE ONLY the provided `df`. DO NOT load files, DO NOT generate fake data, and DO NOT redefine `df`.
2. Verify column names EXACTLY as they appear in the provided metadata. If aggregation is needed, use Pandas before plotting.
3. You MUST import: `import pandas as pd`, `import plotly.express as px`, and `import plotly.io`.
4. The code MUST end with this exact line: `print(plotly.io.to_json(fig))` where `fig` is your Plotly figure object.
5. OUTPUT FORMAT: Return ONLY raw Python code wrapped strictly in `[CODE]` and `[/CODE]` tags. 
   - DO NOT use markdown backticks (```) around or inside the tags.
   - DO NOT include any explanations, greetings, or text outside the tags.

EXAMPLE OUTPUT FORMAT:
[CODE]
import pandas as pd
import plotly.express as px
import plotly.io

# Your code here
fig = px.scatter(df, x='col1', y='col2')
print(plotly.io.to_json(fig))
[/CODE]
"""

SYSTEM_PROMPT_NO_FILE = """
You are an expert Python Data Visualization Engineer.
Your task is to write Python code to create an interactive Plotly Express chart based on the user's request.

CONTEXT:
NO DataFrame is provided. You MUST generate realistic synthetic or mathematical data that perfectly matches the user's request.

STRICT RULES:
1. Generate meaningful data using `numpy` or standard Python libraries, and pack it into a Pandas DataFrame named `df`.
2. You MUST import: `import numpy as np`, `import pandas as pd`, `import plotly.express as px`, and `import plotly.io`.
3. The code MUST end with this exact line: `print(plotly.io.to_json(fig))` where `fig` is your Plotly figure object.
4. OUTPUT FORMAT: Return ONLY raw Python code wrapped strictly in `[CODE]` and `[/CODE]` tags.
   - DO NOT use markdown backticks (```) around or inside the tags.
   - DO NOT include any explanations, greetings, or text outside the tags.

EXAMPLE OUTPUT FORMAT:
[CODE]
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io

x = np.linspace(0, 10, 100)
df = pd.DataFrame({'x': x, 'y': np.sin(x)})
fig = px.line(df, x='x', y='y', title='Sine Wave')
print(plotly.io.to_json(fig))
[/CODE]
"""

SYSTEM_PROMPT_CORRECTION = """
You are an expert Python Debugger and Data Visualization Engineer.
Your previous code generation failed during execution. 

CONTEXT:
The code you provided threw a Runtime Error. You must analyze the error, fix the root cause, and output the COMPLETE corrected code.

STRICT RULES:
1. Identify the exact cause (e.g., KeyError, SyntaxError, missing import, incorrect Plotly method).
2. Provide the COMPLETE, runnable Python code. Do not output partial snippets or "..." placeholders.
3. Maintain all previous requirements: use `df` if it was provided, or generate data if it was not.
4. The code MUST end with: `print(plotly.io.to_json(fig))`.
5. OUTPUT FORMAT: Return ONLY raw Python code wrapped strictly in `[CODE]` and `[/CODE]` tags.
   - DO NOT use markdown backticks (```).
   - DO NOT include any explanations, apologies, or text outside the tags.
"""

def extract_and_run_code(llm_output:str, df: pd.DataFrame=None) -> dict:
    start_tag = "[CODE]"
    end_tag = "[/CODE]"
    
    start_idx = llm_output.find(start_tag)
    end_idx = llm_output.find(end_tag)

    if start_idx == -1 or end_idx == -1:
        return "Error: Model did not wrap code in [CODE]...[/CODE] tags"

    code = llm_output[start_idx+6:end_idx].strip()

    old_stdout = sys.stdout
    redirected_stdout = io.StringIO()
    sys.stdout = redirected_stdout

    try:
        local_vars = {'df':df} if df is not None else {}
        exec(code, {}, local_vars)
        
        output_str = redirected_stdout.getvalue().strip()

        json_start = output_str.find('{"data"')
        if json_start == -1:
            raise ValueError(f'Code executed but did not print valid Plotly JSON. Output: {output_str}')
        return json.loads(output_str[json_start:])
    except Exception as e:
        raise RuntimeError(f'Execution failed: {type(e).__name__}: {e}')
    finally:
        sys.stdout = old_stdout

def DA_agent(user_request:str, df: pd.DataFrame = None, max_attempts: int = 5) -> dict:
    if df is not None:
        buffer = io.StringIO()
        df.info(buf=buffer)
        
        data_context = f"""
        Work with provided DataFrame 'df'.
        Columns:
        {buffer.getvalue()}
        First five rows:
        {df.head(5).to_string()}"""
        
        system_instruction = SYSTEM_PROMPT_WITH_FILE
    else:
        data_context = "No file provided. Analyze the request and take data from it or generate synthetic data yourself."
        system_instruction = SYSTEM_PROMPT_NO_FILE
    
    messages = [
        {'role': 'system', 'content': system_instruction},
        {'role': 'user', 'content': f'{data_context}\n\nUser request: {user_request}'}
    ]
    
    trajectory = []

    for attempt in range(1, max_attempts + 1):
        trajectory.append(f'Attempt {attempt}')
        try:
            response = client.chat.completions.create(
                model="poolside/laguna-xs-2.1:free", #qwen/qwen3.8-27b:free
                messages=messages,
                temperature=0.1
            )
            #print(f"Type of response: {type(response)}")
            #print(f"Response: {response}")
            llm_text = response.choices[0].message.content
            trajectory.append(f"Model reasoning and output:\n{llm_text}")
            messages.append({"role": "assistant", "content": llm_text})

            plotly_data = extract_and_run_code(llm_text, df)
            trajectory.append("Success: Code executed and Plotly JSON parsed.")
            return {
                "status": "success", 
                "data": plotly_data, 
                "trajectory": "\n\n".join(trajectory), 
                "attempts_used": attempt
            }
        
        except Exception as e:
            error_message = str(e)
            trajectory.append(f"Execution error on attempt {attempt}: {error_message}")
            if attempt == max_attempts:
                break
            trajectory.append("Starting self-correction loop...")
            messages[0] = {"role": "system", "content": SYSTEM_PROMPT_CORRECTION}
            messages.append({
                "role": "user", 
                "content": f"Your previous code failed with this error:\n{error_message}\n\nAnalyze and find root cause and then output the COMPLETE corrected code strictly in [CODE]...[/CODE] tags."
            })
            
    return {
        "status": "error", 
        "detail": f"Failed to execute request for {max_attempts} attempts.", 
        "trajectory": "\n\n".join(trajectory)
    }