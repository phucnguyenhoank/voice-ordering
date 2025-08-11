import requests
import json

def llama(messages,
          tools=None):
    """
    Call the LLaMA API to process a user message with optional system content and tools.
    
    Args:
        user_message (str): The user's input message.
        system_content (str, optional): System prompt content. Defaults to receptionist prompt.
        tools (list, optional): List of tool definitions. Defaults to None.
    
    Returns:
        dict: The API response as a dictionary.
    """
    url = "http://localhost:11434/api/chat"
    
    # Construct the payload
    payload = {
        "model": "llama3.2:1b",
        "messages": [],
        "stream": False,
        "options": {
            "seed": 0,
            "temperature": 0.0
        }
    }

    # Add messages
    payload["messages"].extend(messages)
    
    # Add tools if provided
    if tools is not None:
        payload["tools"] = tools
    
    try:
        # Make the API request
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
