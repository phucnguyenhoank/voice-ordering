import os
# import warnings
import requests
import json
import time

# warnings.filterwarnings('ignore')
url = f"http://localhost:11434/api/generate"


import time
def llama(prompt,
          model="llama3.1", 
          temperature=0.0, 
          max_tokens=1024,
          url=url,
          base = 2, # number of seconds to wait
          max_tries=3,
          stream=False,
          context=None):

    data = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }

    
    if context is not None:
        data["context"] = context

    # Allow multiple attempts to call the API incase of downtime.
    # Return provided response to user after 3 failed attempts.    
    wait_seconds = [base**i for i in range(max_tries)]

    for num_tries in range(max_tries):
        try:
            response = requests.post(url, json=data)
            # print(json.dumps(response.json(), indent=2))  # pretty-print whole JSON

            result = response.json()

            # print load time from API (nanoseconds to seconds)
            if "load_duration" in result:
                load_time_sec = result["load_duration"] / 1e9
                print(f"Model load time: {load_time_sec:.3f} seconds")
            
            if "total_duration" in result:
                total_time_sec = result["total_duration"] / 1e9
                print(f"Total time taken for the request: {total_time_sec:.3f} seconds")

            return result["response"], result.get("context", [])
        
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
