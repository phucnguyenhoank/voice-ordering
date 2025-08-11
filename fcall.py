import uuid
from utils2 import llama # Assuming 'utils2.llama' is your LLM call function
import copy
import json
import datetime
import uuid
import csv
import os

data = {
    "categories": [
        {"id": 1, "name": "Burgers"},
        {"id": 2, "name": "Sides"},
        {"id": 3, "name": "Drinks"}
    ],
    "items": [
        {"id": 1, "name": "Cheeseburger", "price": 5.99, "category_id": 1},
        {"id": 2, "name": "Veggie Burger", "price": 5.49, "category_id": 1},
        {"id": 3, "name": "French Fries", "price": 2.99, "category_id": 2},
        {"id": 4, "name": "Coca-Cola", "price": 1.49, "category_id": 3},
        {"id": 5, "name": "Orange Juice", "price": 1.99, "category_id": 3}
    ],
    "discounts": [
        {"discount_percentage": 0.10, "item_ids": [1, 4]},
        {"discount_percentage": 0.05, "item_ids": [3]},
        {"discount_percentage": 0.20, "item_ids": [5]}
    ]
}
MENU_DATA = copy.deepcopy(data)

def calculate_total(order, create=False, saved_folder="orders"):
    total = 0.0
    subtotal = 0.0
    order_details = []
    discounts_applied = []
    for ord_item in order:
        item_id = ord_item["item_id"]
        quantity = ord_item["quantity"]
        item = next(i for i in data["items"] if i["id"] == item_id)
        name = item["name"]
        price = item["price"]
        discount = 0.0
        for disc in data["discounts"]:
            if item_id in disc["item_ids"]:
                discount = disc["discount_percentage"]
                break
        line_total = round(price * quantity, 2)
        subtotal += line_total
        per_item_discount = round(price * discount, 2)
        discount_amount = per_item_discount * quantity
        if discount_amount > 0:
            description = f"{int(discount * 100)}% off on {name}"
            discounts_applied.append({"description": description, "amount": round(-discount_amount, 2)})
        discounted_line_total = line_total - discount_amount
        total += discounted_line_total
        order_details.append({
            "name": name,
            "quantity": quantity,
            "price_per_item": price,
            "line_total": line_total
        })

    subtotal = round(subtotal, 2)
    total = round(total, 2)

    result = {
        "order_details": order_details,
        "subtotal": subtotal,
        "discounts_applied": discounts_applied,
        "total_price": total
    }

    order_id = None
    created_at = None
    if create:
        now = datetime.datetime.now()
        dt_string = now.strftime("%Y%m%d_%H%M%S")
        order_id = f"{uuid.uuid4().hex}"
        created_at = now.isoformat()
        os.makedirs(saved_folder, exist_ok=True)
        filename = os.path.join(saved_folder, f"order_{order_id}_{dt_string}.csv")
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Order ID", "Created At", "Item Name", "Quantity", "Price", "Discount", "Subtotal"])
            for det in order_details:
                # Recompute per line discount for CSV
                item_discount = next((d["discount_percentage"] for d in data["discounts"] if ord_item["item_id"] in d["item_ids"]), 0.0)
                det_subtotal = round(price * (1 - item_discount) * quantity, 2)
                writer.writerow([order_id, created_at, det["name"], det["quantity"], price, item_discount, det_subtotal])
        result["order_id"] = order_id
        result["created_at"] = created_at

    return result

def get_menu(categories=None):
    # If categories is None or not provided, return the full data
    if not categories:
        print('empty category:', categories)
        return data
    
    # Filter categories by provided names
    filtered_categories = [cat for cat in data["categories"] if cat["name"] in categories]
    filtered_category_ids = {cat["id"] for cat in filtered_categories}
    
    # Filter items by category_id in filtered categories
    filtered_items = [item for item in data["items"] if item["category_id"] in filtered_category_ids]
    filtered_item_ids = {item["id"] for item in filtered_items}
    
    # Filter discounts to only include item_ids that are in filtered_items
    filtered_discounts = []
    for disc in data["discounts"]:
        # Keep only item_ids that are in filtered_items
        valid_item_ids = [item_id for item_id in disc["item_ids"] if item_id in filtered_item_ids]
        if valid_item_ids:  # Only include discount if it applies to at least one valid item
            filtered_discounts.append({
                "discount_percentage": disc["discount_percentage"],
                "item_ids": valid_item_ids
            })
    
    # Return new data structure with filtered categories, items, and discounts
    return {
        "categories": filtered_categories,
        "items": filtered_items,
        "discounts": filtered_discounts
    }

# --- Main Application Loop ---
def print_content(message):
    role = message["role"]
    content = message["content"]
    print(f"{role}> {content}")

if __name__ == "__main__":
    # Updated tools with adjusted parameters
    default_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_menu",
                "description": "Get the current fast food menu, optionally filtered by categories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of menu category names: 'Burgers', 'Sides', or 'Drinks'"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_total",
                "description": "Calculates the total price for a list of items and applies discounts. The item used to calculate must exist in the current menu. The parameter 'create' must be true to save the order when the confirmed otherwise it will not. Use this to show the customer the order details before they confirm.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "description": "List of items to order.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer", "description": "ID of the menu item."},
                                    "quantity": {"type": "integer", "description": "Number of this item to order."}
                                },
                                "required": ["item_id", "quantity"]
                            }
                        },
                        "create": {
                            "type": "boolean",
                            "description": "If true, save the order to a CSV file, if false, don't save the order."
                        }
                    },
                    "required": ["order"]
                }
            }
        }
    ]

    greeting_prompt = "Thank you for choosing us, what would you like to eat today?"
    system_prompt = f"""
    You are a friendly and efficient fast-food restaurant receptionist that takes quick order conversations. 
    Your job is to take customer orders, offer suggestions, and direct them to the next step.

    Here are your instructions:
    - Take the order: Greet the customer first and then ask their order.
    - Suggest items: Recommend popular or complementary menu items from the `MENU` if you are asked.
    - Show details: Use the 'get_menu' with the optional parameter 'categories' (a list of category names) to get item information the user needs.
    - Calculate total price: You can only use the items from the `MENU` to show the full order details and total price to the user. Use item IDs from the MENU for the order.
    - Ask for confirmation: After showing the order, politely confirm the order with the customer.
    - Finalize the order: Once confirmed, use the 'calculate_total' function with 'create=true' to finalize the order, say thanks, and direct the customer to the payment window.

    Here is the `MENU`:
    {MENU_DATA}
    """

    
    messages = [
        {"role": "system", "content": system_prompt},

        # 1-shot example starts
        {"role": "assistant", "content": greeting_prompt},
        {"role": "user", "content": "I want 2 Burgers please"},
        {"role": "assistant", "content": "We have Veggie Burger $5.49 and Cheeseburger $5.99, we are having 10% discount on Cheeseburger. What would you like?"},
        {"role": "user", "content": "2 cheese burgers please"},
        {"role": "assistant", "content": "Ok, would you like some drinks? We are having 10% off on Coca-Cola and 20% off on Orange Juice."},
        {"role": "user", "content": "no"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "calculate_total", "arguments": {"order": [{"item_id": 1, "quantity": 2}], "create": True}}}
        ]},
        {"role": "tool", "name": "calculate_total", "content": json.dumps({
            "order_details": [
                {"name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98}
            ],
            "subtotal": 11.98,
            "discounts_applied": [{"description": "10% off on Cheeseburger", "amount": -1.2}],
            "total_price": 10.78,
            "order_id": "example_order_id",
            "created_at": "2025-08-11T00:00:00"
        })},
        {"role": "assistant", "content": "Great, your order was created with ID example_order_id: 2 Cheeseburgers, each $5.99. With 10% off, you only pay $10.78. Thank you and please go to the payment window ahead."}
        # 1-shot example ends
    ]

    
    # Map function names to the actual functions for dispatch
    available_tools = {
        "get_menu": get_menu,
        "calculate_total": calculate_total
    }

    print("-----------FastFood Restaurant-------------")
    print(f"assistant> {greeting_prompt}")
    messages.append({"role": "assistant", "content": greeting_prompt})

    while True:
        user_prompt = input('user> ')
        messages.append({"role": "user", "content": user_prompt})

        response = llama(messages=messages, tools=default_tools)
        message = response["message"]

        print(f"response:{json.dumps(response, indent=4)}")

        if message.get("tool_calls"):
            
            tool_calls = message["tool_calls"]
            messages.append(message)  # Append assistant's message with tool calls

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                if function_name in available_tools:
                    function_to_call = available_tools[function_name]
                    arguments = tool_call["function"].get("arguments", {})
                    tool_result = function_to_call(**arguments)
                else:
                    tool_result = {"error": f"Unknown function: {function_name}"}

                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            followup = llama(messages=messages, tools=default_tools)
            print_content(followup["message"])
            messages.append(followup["message"])
        else:
            print_content(message)
            messages.append(message)
        
        