import uuid
import pandas as pd
import os
from utils2 import llama
import json

# CSV file for orders
ORDERS_CSV = "orders.csv"

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

def create_order(items):
    """
    Creates an order from a list of items, calculates total price, generates an order ID,
    and appends it to orders.csv with confirm=False.
    
    :param items: List of item names (e.g., ["Classic Burger", "Coke"])
    :return: Dictionary with order_id and total_price
    """
    menu = get_menu()
    total_price = 0.0
    valid_items = []

    # Validate items and calculate total price
    for item in items:
        found = False
        for category, category_items in menu.items():
            for menu_item in category_items:
                if menu_item["name"].lower() == item.lower():
                    total_price += menu_item["price"]
                    valid_items.append(item)
                    found = True
                    break
            if found:
                break
        if not found:
            return {"error": f"Item '{item}' not found on the menu"}

    # Generate unique order ID
    order_id = str(uuid.uuid4())

    # Create or append to orders.csv
    order_data = {"order_id": order_id, "total_price": round(total_price, 2), "confirm": False}
    df = pd.DataFrame([order_data])
    
    if os.path.exists(ORDERS_CSV):
        df.to_csv(ORDERS_CSV, mode='a', header=False, index=False)
    else:
        df.to_csv(ORDERS_CSV, mode='w', header=True, index=False)

    return {"order_id": order_id, "total_price": round(total_price, 2)}

def confirm_order(order_id):
    """
    Updates the confirm status to True for the specified order ID in orders.csv.
    
    :param order_id: The ID of the order to confirm
    :return: True if the order was found and updated, False otherwise
    """
    if not os.path.exists(ORDERS_CSV):
        return False

    # Read the CSV file
    df = pd.read_csv(ORDERS_CSV)

    # Check if order_id exists
    if order_id in df["order_id"].values:
        # Update confirm status
        df.loc[df["order_id"] == order_id, "confirm"] = True
        # Write back to CSV
        df.to_csv(ORDERS_CSV, index=False)
        return True
    return False

def print_content(message):
    role = message["role"]
    content = message["content"]
    print(f"{role}> {content}")

# Example usage:
if __name__ == "__main__":
    system_prompt = """
    You are a friendly and efficient Receptionist at a fast food restaurant.
    Always:
    - Suggest dishes from the menu.
    - Show the full order details and total price clearly.
    - Politely ask for confirmation before sending the order to the chef.
    - Thank the customer after completion and offer further assistance.
    - If the customer is finished, say goodbye and express that you hope to see them again.
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
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "Create an order from a list of item names and return the order ID and total price.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of item names to order (e.g., ['Classic Burger', 'Coke'])"
                        }
                    },
                    "required": ["items"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "confirm_order",
                "description": "Confirm if an order exists by its order ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The ID of the order to confirm"
                        }
                    },
                    "required": ["order_id"]
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
        
        # Handle tool calls
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                # Append the assistant's tool call to messages
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call]
                })

                # Execute the appropriate function
                if function_name == "get_menu":
                    category = arguments.get("category", None)
                    result = get_menu(category)
                elif function_name == "create_order":
                    items = arguments.get("items", [])
                    result = create_order(items)
                elif function_name == "confirm_order":
                    order_id = arguments.get("order_id", "")
                    result = confirm_order(order_id)
                else:
                    result = {"error": f"Unknown function: {function_name}"}

                # Append the tool result to messages
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result)
                })

                # Call the API again with the updated messages
                result = llama(messages=messages, tools=default_tools)
                print_content(result["message"])
        else:
            # If no tool calls, print the assistant's response and update messages
            role = message["role"]
            content = message["content"]
            print(f"{role}> {content}")
            messages.append({
                "role": role,
                "content": content
            })