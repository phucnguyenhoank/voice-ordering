import os
# import warnings
import requests
import json
import time

# warnings.filterwarnings('ignore')
url = f"http://localhost:11434/api/generate"


import time
def llama(prompt, 
          add_inst=True, 
          model="llama3.1", 
          temperature=0.0, 
          max_tokens=1024,
          verbose=False,
          url=url,
          base = 2, # number of seconds to wait
          max_tries=3,
          stream=False):
    
    if add_inst:
        prompt = f"[INST]{prompt}[/INST]"

    if verbose:
        print(f"Prompt:\n{prompt}\n")
        print(f"model: {model}")

    data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

    # Allow multiple attempts to call the API incase of downtime.
    # Return provided response to user after 3 failed attempts.    
    wait_seconds = [base**i for i in range(max_tries)]

    for num_tries in range(max_tries):
        try:
            response = requests.post(url, json=data)
            # print(json.dumps(response.json(), indent=2))  # pretty-print whole JSON
            return response.json()["response"]
        except Exception as e:
            if response.status_code != 500:
                return response.json()

            print(f"error message: {e}")
            print(f"response object: {response}")
            print(f"num_tries {num_tries}")
            print(f"Waiting {wait_seconds[num_tries]} seconds before automatically trying again.")
            time.sleep(wait_seconds[num_tries])
            
    print(f"Tried {max_tries} times to make API call to get a valid response object")
    print("Returning provided response")
    return response
