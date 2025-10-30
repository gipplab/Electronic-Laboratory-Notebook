
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re
import json
import time
from openai import OpenAI
from Exp_Main.models import ExpBase

from Analysis.RSD import RSD
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# --- CONFIGURATION ---
# IMPORTANT: Store these securely, e.g., as environment variables
CODE_GENERATOR_ASSISTANT_ID = ""#Add
DEBUGGER_ASSISTANT_ID = ""#Add
client = OpenAI(
  api_key=""#Add
)

# This view just renders the HTML page for the chat
def chat_page_view(request):
    # Django will now look for AI_Assistant/templates/chat.html
    return render(request, 'AI_Assistant/chat.html')

@csrf_exempt # For simplicity in this example
def start_chat_view(request):
    if request.method == 'POST':
        thread = client.beta.threads.create()
        return JsonResponse({'thread_id': thread.id})
    return JsonResponse({'error': 'Invalid request method'}, status=405)



def extract_python_code(text):
    """Extracts Python code from a string, stripping markdown and explanations."""
    # Regex to find a python code block
    match = re.search(r'```(python)?\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(2).strip()
    
    # If no markdown, assume the whole text might be code, but this is less reliable
    return text.strip()

def execute_dynamic_script(code_string):
    """
    Executes a multi-line script and looks for either a Plotly figure
    or a simple return value.
    """
    # Create a namespace for the script to run in.
    # Pre-populate it with all the libraries the AI can use.
    script_namespace = {
        'RSD': RSD,
        'go': go,
        'pd': pd,
        'np': np,
        'ExpBase': ExpBase,
    }
    
    # Execute the multi-line script. The results (variables) will be
    # stored in our script_namespace dictionary.
    exec(code_string, script_namespace)
    
    # Check if the script produced a Plotly figure.
    if 'fig' in script_namespace and isinstance(script_namespace['fig'], go.Figure):
        fig_object = script_namespace['fig']
        # Convert the figure to JSON for the frontend
        plot_json = fig_object.to_json()
        return {'type': 'plot', 'data': plot_json}
    else:
        # If no plot, assume it was a simple ORM query.
        # This part might need to be smarter, but it's a good start.
        # We find the last expression in the code to evaluate it.
        last_line = code_string.strip().split('\n')[-1]
        result = eval(last_line, script_namespace)
        return {'type': 'text', 'data': str(result)}

def execute_investigative_code(code_string: str) -> str:
    """
    A safer execution environment specifically for the debugger's
    investigative commands. This environment is pre-loaded with
    the key classes the debugger needs to "see".
    """
    # This is a critical safety check.
    if 'import ' in code_string:
        raise ValueError("Dynamic imports are not allowed in this environment.")
        
    # --- THIS IS THE CORRECT 'WORKBENCH' FOR THE DEBUGGER ---
    # We create a dictionary that defines all the "global variables"
    # that the debugger's code can access.
    execution_context = {
        # The main Django model is available.
        'ExpBase': ExpBase,
        
        # The RSD class is now available by name.
        # This is the most important fix.
        'RSD': RSD,
        
        # We also provide the safe, built-in introspection tools.
        'dir': dir,
        'type': type,
        'hasattr': hasattr,
        'help': help, # It tried to use help(), so let's provide it.
    }
    
    # We use eval() to execute the single line of investigative code
    # within the carefully controlled context.
    return str(eval(code_string, execution_context))



def extract_json_from_string(text):
    """
    Finds and extracts the first JSON object or array from a string
    that might be wrapped in markdown code blocks or other text.
    """
    # Regex to find a JSON object enclosed in ```json ... ``` or just ``` ... ```
    match = re.search(r'```(json)?\s*({.*?})\s*```', text, re.DOTALL)
    
    if match:
        # If found, return the captured JSON part
        return match.group(2)
    
    # If no markdown block is found, assume the whole string might be JSON
    # and try to find the first '{' to the last '}'
    match = re.search(r'({.*?})', text, re.DOTALL)
    if match:
        return match.group(1)
        
    # If all else fails, return the original text
    return text

# THE NEW INVESTIGATIVE DEBUGGER FUNCTION
def run_investigative_debugger(user_goal, failed_code, error_message):
    print("\n--- [DEBUGGER] Starting investigative session. ---")
    
    # We can create a temporary, dedicated thread for this debugging session
    debug_thread = client.beta.threads.create()

    # The initial prompt for the debugger
    initial_debug_prompt = (
        "Debugging Task:\n"
        f"  - User's Goal: '{user_goal}'\n"
        f"  - Failed Code: `{failed_code}`\n"
        f"  - Error Message: `{error_message}`\n\n"
        "Please begin your investigation."
    )
    client.beta.threads.messages.create(
        thread_id=debug_thread.id,
        role="user",
        content=initial_debug_prompt
    )

    max_investigation_steps = 10
    for i in range(max_investigation_steps):
        print(f"  [DEBUGGER] Investigation Step {i + 1}")
        
        # Run the debugger assistant
        run = client.beta.threads.runs.create(
            thread_id=debug_thread.id,
            assistant_id=DEBUGGER_ASSISTANT_ID
        )
        while run.status not in ['completed', 'failed']:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=debug_thread.id, run_id=run.id)
        
        if run.status == 'failed':
            return None, "Debugger run failed."

        # Get the debugger's response
        messages = client.beta.threads.messages.list(thread_id=debug_thread.id, limit=1)
        response_text = messages.data[0].content[0].text.value
        
        # Clean the response before parsing
        cleaned_text = extract_json_from_string(response_text)
        
        try:
            response_json = json.loads(cleaned_text) # Parse the cleaned text
            action = response_json.get("action")
            code_to_run = response_json.get("code")
            print(f"  > Debugger action: {action}, Code: `{code_to_run}`")
        except (json.JSONDecodeError, AttributeError):
            return None, "Debugger returned invalid JSON response, even after cleaning."

        if action == "SOLVE":
            # The debugger thinks it has the final answer
            print("  > Debugger proposed a final solution.")
            return code_to_run, None # Return the final code
        
        elif action == "INVESTIGATE":
            # The debugger wants to run exploratory code
            try:
                print(f"  > Executing investigative code: `{code_to_run}`")
                
                # --- THIS IS THE FIX ---
                # Call the helper function that has the rich context.
                investigation_result = execute_investigative_code(code_to_run)
                
                print(f"  > Investigation result: {investigation_result}")
                # Feed the result back to the debugger
                client.beta.threads.messages.create(
                    thread_id=debug_thread.id,
                    role="user",
                    content=f"Investigation Result: `{investigation_result}`"
                )
            except Exception as e:
                # The exploratory code itself failed. Tell the debugger.
                print(f"  >! Investigative code failed: {e}")
                client.beta.threads.messages.create(
                    thread_id=debug_thread.id,
                    role="user",
                    content=f"Your investigative command failed with error: `{str(e)}`"
                )
        else:
            return None, "Debugger returned an unknown action."
            
    return None, "Debugger exceeded max investigation steps."

# --- Main view ---
# AI_Assistant/views.py

@csrf_exempt
def ask_assistant_view(request):
    # --- Step 1: Get the request data ---
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        thread_id = data.get('thread_id')
        user_message = data.get('message')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not thread_id or not user_message:
        return JsonResponse({'error': 'Missing thread_id or message'}, status=400)

    # --- Step 2: Initial attempt with CodeGenerator ---
    print("\n--- [CODER] Starting initial code generation. ---")
    
    # Add the user's message to the thread for the Coder
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )
    
    # Run the Coder assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=CODE_GENERATOR_ASSISTANT_ID
    )
    while run.status not in ['completed', 'failed']:
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
    
    if run.status == 'failed':
        return JsonResponse({'error': 'CodeGenerator assistant run failed.'}, status=500)
        
    messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
    
    generated_code_raw = messages.data[0].content[0].text.value
    print(f"  > Coder generated (raw): `{generated_code_raw}`")

    generated_code_raw = messages.data[0].content[0].text.value
    generated_code = extract_python_code(generated_code_raw)
    print(f"  > Coder generated (cleaned): `{generated_code}`")
    
    # --- NEW VALIDATION STEP ---
    # Check if the generated code is just a simple error message or looks invalid.
    # This is a basic check. Real Python code will have more substance.
    # We look for keywords that should be in valid code.
    valid_keywords = ['RSD', 'ExpBase', 'fig =', 'go.']
    if not any(keyword in generated_code for keyword in valid_keywords):
        print(f"  >! Coder returned an invalid response, not code. Aborting.")
        # Return a user-friendly error instead of escalating to the debugger.
        error_message = f"I'm sorry, I was unable to generate the code for your request. The assistant responded: '{generated_code}'"
        return JsonResponse({
            'type': 'text',
            'data': error_message,
            'generated_code': 'Error: Assistant did not generate valid code.'
        }, status=400)
    
    # --- Step 3: Try to execute the (now validated) Coder's code ---
    try:
        print("  > Executing generated script...")
        result_dict = execute_dynamic_script(generated_code)
        
        print("  > SUCCESS: Coder's code worked on the first try.")
        return JsonResponse({
            'type': result_dict.get('type'),
            'data': result_dict.get('data'),
            'generated_code': generated_code
        })
    
    except Exception as e:
        # --- Step 4: If it fails, escalate to the Debugger ---
        print(f"  >! Coder failed. Escalating to Investigative Debugger. Error: {e}")
        
        # --- The `failed_code` passed to the debugger should be the CLEANED version ---
        corrected_code, debug_error = run_investigative_debugger(
            user_goal=user_message,
            failed_code=generated_code, # Pass the cleaned code
            error_message=str(e)
        )
        
        if debug_error:
            return JsonResponse({'error': debug_error}, status=500)
            
        # Now, try to execute the final code from the debugger
        try:
            # --- UPDATE HERE: Use the new dynamic script executor again ---
            print("  > Executing Debugger's final solution...")
            final_result_dict = execute_dynamic_script(corrected_code)
            
            print("  > SUCCESS: Debugger's final solution worked.")
            return JsonResponse({
                'type': final_result_dict.get('type'),
                'data': final_result_dict.get('data'),
                'generated_code': corrected_code
            })
        except Exception as final_e:
            print(f"  >! Debugger's final solution also failed: {final_e}")
            return JsonResponse({
                'error': f"The debugger's final solution also failed: {final_e}",
                'generated_code': corrected_code
            }, status=400)