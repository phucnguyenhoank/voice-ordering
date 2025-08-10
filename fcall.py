import uuid
import json
import csv
from datetime import datetime
from pathlib import Path
from utils2 import llama # Assuming 'utils2.llama' is your LLM call function

# --- Simplified Data and Functions ---

# 1. Menu data is now a global constant with more structured discount info
MENU_DATA = {
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
        # Added type and metadata for programmatic application
        {"description": "Buy 1 Get 1 Free on Cheeseburger", "valid_until": "2025-08-31", "type": "BOGO", "item_name": "Cheeseburger"},
        {"description": "20% off on all drinks", "valid_until": "2025-08-20", "type": "PERCENTAGE", "category_id": 3, "value": 20}
    ]
}

def get_menu(category: str | None = None):
    """
    Returns the menu, optionally filtered by category.
    Includes categories, items, and currently active discounts.
    """
    menu = json.loads(json.dumps(MENU_DATA)) # Deep copy
    today = datetime.now().date()
    
    # Filter for active discounts
    active_discounts = [
        d for d in menu["discounts"]
        if datetime.strptime(d["valid_until"], "%Y-%m-%d").date() >= today
    ]
    menu["discounts"] = active_discounts

    # If no category is provided, return the full menu
    if not category:
        return menu

    # --- Filter by category if provided ---
    cat_id = None
    for c in menu["categories"]:
        if category == c["name"]:
            cat_id = c["id"]
            break
    
    if cat_id is not None:
        # If category is found, filter the items
        filtered_items = [it for it in menu["items"] if it["category_id"] == cat_id]
        menu["items"] = filtered_items
    else:
        # If category doesn't exist, return no items
        menu["items"] = []

    return menu

def calculate_total(items: list[dict]):
    """
    Calculates the total price for an order, including discounts.
    This should be used to present the order to the customer for confirmation.
    """
    menu = get_menu()
    item_lookup = {it["name"].lower(): it for it in menu["items"]}
    
    order_details = []
    subtotal = 0.0
    
    # Calculate subtotal from items
    items = items.replace("'", '"')
    print(f'items:{items}')
    print(type(items))
    items = json.loads(items)
    for item_order in items:
        name = item_order["name"].lower()
        quantity = int(item_order.get("quantity", 1))

        if name in item_lookup and quantity > 0:
            item_data = item_lookup[name]
            price = item_data["price"]
            subtotal += price * quantity
            order_details.append({
                "name": item_data["name"],
                "quantity": quantity,
                "price_per_item": price,
                "line_total": round(price * quantity, 2)
            })

    # Apply discounts
    discounts_applied = []
    total_discount_amount = 0.0

    for discount in menu["discounts"]:
        if discount["type"] == "BOGO":
            for order_item in order_details:
                if order_item["name"] == discount["item_name"] and order_item["quantity"] >= 2:
                    discount_amount = (order_item["quantity"] // 2) * order_item["price_per_item"]
                    total_discount_amount += discount_amount
                    discounts_applied.append({"description": discount["description"], "amount": round(-discount_amount, 2)})
        
        elif discount["type"] == "PERCENTAGE":
            applicable_total = sum(
                od["line_total"] for od in order_details 
                if item_lookup[od["name"].lower()]["category_id"] == discount["category_id"]
            )
            if applicable_total > 0:
                discount_amount = (applicable_total * discount["value"]) / 100
                total_discount_amount += discount_amount
                discounts_applied.append({"description": discount["description"], "amount": round(-discount_amount, 2)})

    return {
        "order_details": order_details,
        "subtotal": round(subtotal, 2),
        "discounts_applied": discounts_applied,
        "total_price": round(subtotal - total_discount_amount, 2)
    }

def create_order(items: list[dict], total_price: float):
    """
    Saves a CONFIRMED order to a CSV file. Customer name is not saved.
    """
    order_id = str(uuid.uuid4())
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = Path("orders.csv")
    file_exists = file_path.is_file()

    with open(file_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            # "CustomerName" has been removed from the header
            writer.writerow(["OrderID", "Items", "TotalPrice", "OrderDate"])
        
        # The row no longer includes a customer name
        writer.writerow([
            order_id,
            json.dumps(items),
            f"{total_price:.2f}",
            order_date
        ])
        
    return {
        "status": "success",
        "order_id": order_id,
        "message": f"Order {order_id} confirmed! Please head to the payment window."
    }

# --- Simplified Tool Definitions ---

# 2. Tools are redefined for a clearer, step-by-step ordering process
default_tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_total",
            "description": "Calculates the total price for a list of items and applies discounts. The item used to calculate must exist in the current menu. Use this to show the customer the order details before they confirm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of items to order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Name of the menu item."},
                                "quantity": {"type": "integer", "description": "Number of this item to order."}
                            },
                            "required": ["name", "quantity"]
                        }
                    }
                },
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Saves a confirmed order to the system. Customer name is not needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Final list of items in the order.",
                        "items": {
                             "type": "object",
                             "properties": {"name": {"type": "string"}, "quantity": {"type": "integer"}},
                             "required": ["name", "quantity"]
                        }
                    },
                    "total_price": {
                        "type": "number",
                        "description": "The final confirmed total price from calculate_total."
                    }
                },
                "required": ["items", "total_price"]
            }
        }
    }
]

# --- Main Application Loop ---
def print_content(message):
    role = message["role"]
    content = message["content"]
    print(f"{role}> {content}")

if __name__ == "__main__":
    greeting_prompt = "Thank for choosing us, what would you like to eat today?"
    system_prompt = f"""
    You are a friendly and efficient fast-food restaurant receptionist that takes quick order conversations. 
    Your job is to take customer orders, offer suggestions, and direct them to the next step.

    Here are your instructions:
    - Take the order: Greet the customer first and then ask their order.
    - Suggest items: Recommend popular or complementary menu items from the `MENU` if you are asked.
    - Show details: Use the 'get_menu' with the optional parameter 'category' to get item information the user needs.
    - Calculate total price: You can only use the items from the `MENU` to show the full order details and total price to the user.
    - Ask for confirmation: After showing the order, politely confirm the order with the customer.
    - Finalize the order: Once confirmed, use the 'create_order' function to finalize the order, say thanks, and direct the customer to the payment window.

    Here is the `MENU`:
    {MENU_DATA}
    """

    
    messages = [
        {"role": "system", "content": system_prompt},

        # 1-shot example starts
        {"role": "assistant", "content": greeting_prompt},
        {"role": "user", "content": "I want 2 Burgers please"},
        {"role": "assistant", "content": "We have Veggie Burger $5.49 and Cheeseburger $5.99, we are having a discount on Cheeseburger, buy 1 Get 1 Free. What would you like?"},
        {"role": "user", "content": "2 cheese burgers please"},
        {"role": "assistant", "content": "Ok, would you like some drinks? We are also having 20% off on all drinks."},
        {"role": "user", "content": "no"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "calculate_total", "arguments": {"items": [{"name": "Cheeseburger", "quantity": 2}]}}}
        ]},
        {"role": "tool", "name": "calculate_total", "content": json.dumps({
            "order_details": [
                {"name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98}
            ],
            "subtotal": 11.98,
            "discounts_applied": [{"description": "Buy 1 Get 1 Free", "amount": -5.99}],
            "total_price": 5.99
        })},
        {"role": "assistant", "content": "Great, your order was created: 2 Cheeseburgers, each $5.99. With Buy 1 Get 1 Free, you only pay for 1 burger. Total price is $5.99. Thank you and please go to the payment window ahead."}
        # 1-shot example ends

        # Now start the real conversation
        # {"role": "assistant", "content": greeting_prompt}
    ]

    
    # 3. Map function names to the actual functions for dispatch
    available_tools = {
        "get_menu": get_menu,
        "calculate_total": calculate_total,
        "create_order": create_order,
    }

    print("-----------FastFood Restaurant-------------")
    print(f"{greeting_prompt}")

    while True:
        user_prompt = input('user> ')
        messages.append({"role": "user", "content": user_prompt})

        response = llama(messages=messages, tools=default_tools)
        message = response["message"]

        if message.get("tool_calls"):
            tool_calls = message["tool_calls"]
            messages.append(message) # Append assistant's message with tool calls

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
        
        