from utils2 import llama
import json

def get_menu(category=None):
    menu = {
        "burgers": [
            {"name": "Classic Burger", "price": 5.99, "calories": 650},
            {"name": "Double Cheese", "price": 7.99, "calories": 950}
        ],
        "sides": [
            {"name": "Fries (Large)", "price": 2.49, "calories": 450},
            {"name": "Onion Rings", "price": 2.99, "calories": 420}
        ],
        "drinks": [
            {"name": "Coke", "price": 1.50, "size": "500ml"},
            {"name": "Water", "price": 1.00, "size": "500ml"}
        ]
    }
    if category:
        return {category: menu.get(category, [])}
    return menu

def print_content(message):
    role = message["role"]
    content = message["content"]
    print(f"{role}> {content}")

# Example usage:
if __name__ == "__main__":
    system_prompt = """
    As a Receptionist, 
    your goal is to suggest dishes from the fast food menu, 
    and help the user place an order by sending what they want to the kitchen.
    """

    messages = [
        {
            "role": "system",
            "content": system_prompt.strip(),
        }
    ]

    default_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_menu",
                "description": "Get the current fast food menu, optionally filtered by category.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional menu category: 'burgers', 'sides', or 'drinks'"
                        }
                    }
                }
            }
        }
    ]

    print("WELCOME")
    print("-----------------------")
    
    while True:
        # Get user's prompt
        user_prompt = input('user>')
        messages.append({
            "role": "user",
            "content": user_prompt
        })

        # Get the message from the response
        response = llama(messages=messages, tools=default_tools)
        message = response["message"]
        
        # Hold on printing the response message if there is at least a tool call
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                # Call the get_menu function if requested
                if function_name == "get_menu":
                    category = arguments.get("category", None)
                    # Execute the get_menu function
                    menu_result = get_menu(category)
                    
                    # Append the tool result to messages
                    messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(menu_result)
                    })

                    # Call the API again with the updated messages
                    result = llama(messages=messages, tools=default_tools)
                    print_content(result["message"])
                    # print("Response after tool call:", json.dumps(result, indent=2))
        else:
            # If no tool calls, just print the assistant's response message and update the context
            role = message["role"]
            content = message["content"]
            print(f"{role}: {content}")
            messages.append({
                "role": role,
                "content": content
            })
        
    