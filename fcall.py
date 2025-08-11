import uuid
from utils2 import llama # Assuming 'utils2.llama' is your LLM call function
import copy
import json
import datetime
import uuid
import csv
import os
import pandas as pd

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

def _load_order(order):
    """Accept list or JSON string and return list of dicts."""
    if isinstance(order, str):
        return json.loads(order)
    return order

def _get_item(item_id):
    return next(i for i in MENU_DATA["items"] if i["id"] == item_id)

def _get_item_discount(item_id):
    return next((d["discount_percentage"] for d in MENU_DATA["discounts"] if item_id in d["item_ids"]), 0.0)

def calculate_total(order):
    """
    Read-only preview.
    order: list of {"item_id": int, "quantity": int} OR JSON string of same
    returns: dict with order_details, subtotal, discounts_applied, total_price
    """
    order = _load_order(order)
    subtotal = 0.0
    total = 0.0
    order_details = []
    discounts_applied = []

    for ord_item in order:
        item_id = ord_item["item_id"]
        qty = int(ord_item["quantity"])
        item = _get_item(item_id)
        price = float(item["price"])
        discount = float(_get_item_discount(item_id))  # decimal, e.g. 0.1

        line_total = round(price * qty, 2)
        line_discount_amount = round(price * qty * discount, 2)

        subtotal += line_total
        total += (line_total - line_discount_amount)

        order_details.append({
            "item_id": item_id,
            "name": item["name"],
            "quantity": qty,
            "price_per_item": price,
            "line_total": round(line_total, 2),
            "line_discount": round(line_discount_amount, 2),
            "discount_pct": discount
        })

        if line_discount_amount > 0:
            discounts_applied.append({
                "description": f"{int(discount*100)}% off on {item['name']}",
                "amount": -round(line_discount_amount, 2)
            })

    subtotal = round(subtotal, 2)
    total = round(total, 2)

    return {
        "order_details": order_details,
        "subtotal": subtotal,
        "discounts_applied": discounts_applied,
        "total_price": total
    }

def create_order(order, saved_folder="orders"):
    """
    Finalize & save order using pandas. Returns order metadata + same totals.
    """
    order = _load_order(order)
    totals = calculate_total(order)

    now = datetime.datetime.now()
    order_id = uuid.uuid4().hex
    created_at = now.isoformat()

    # Build rows for DataFrame
    rows = []
    for det in totals["order_details"]:
        rows.append({
            "order_id": order_id,
            "created_at": created_at,
            "item_id": det["item_id"],
            "item_name": det["name"],
            "quantity": det["quantity"],
            "price_per_item": det["price_per_item"],
            "discount_pct": det["discount_pct"],
            "line_total": det["line_total"],
            "line_discount": det["line_discount"],
            "line_after_discount": round(det["line_total"] - det["line_discount"], 2)
        })

    df = pd.DataFrame(rows)
    os.makedirs(saved_folder, exist_ok=True)
    filename = os.path.join(saved_folder, f"order_{order_id}.csv")
    df.to_csv(filename, index=False, encoding="utf-8")

    # Attach order id and created_at to the returned result
    totals["order_id"] = order_id
    totals["created_at"] = created_at
    totals["saved_as"] = filename
    return totals

def get_menu(category_ids=None):
    # If category_ids is None or empty, return the full data
    if not category_ids:
        return data

    if isinstance(category_ids, str):
        category_ids = json.loads(category_ids)
    
    # Filter categories by provided IDs
    filtered_categories = [cat for cat in data["categories"] if cat["id"] in category_ids]
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
    # ----------------- Replace these three variables -----------------

    # 1) default_tools: explicit, non-ambiguous tool schema
    default_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_menu",
                "description": "Get the current fast food menu, optionally filtered by category IDs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Optional list of menu category IDs: 1 (Burgers), 2 (Sides), 3 (Drinks)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_total",
                "description": "Read-only preview: returns order_details, subtotal, discounts_applied and total_price. Does NOT save files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "description": "List of items to order (preview only).",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer", "description": "ID of the menu item."},
                                    "quantity": {"type": "integer", "description": "Number of this item to order."}
                                },
                                "required": ["item_id", "quantity"]
                            }
                        }
                    },
                    "required": ["order"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "Save a confirmed order to CSV (using pandas) and return order_id, created_at and saved filename. Call this only after customer confirmation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "description": "Confirmed list of items to persist to disk.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer"},
                                    "quantity": {"type": "integer"}
                                },
                                "required": ["item_id", "quantity"]
                            }
                        }
                    },
                    "required": ["order"]
                }
            }
        }
    ]

    # 2) system_prompt: instruct assistant to preview with calculate_total and finalize with create_order
    greeting_prompt = "Thank you for choosing us, what would you like to eat today?"

    system_prompt = f"""
    You are a friendly and efficient fast-food restaurant receptionist that takes quick order conversations.
    Your job is to take customer orders, offer suggestions, and direct them to the next step.

    Here are your instructions:
    - Greet the customer and ask their order.
    - Suggest items: recommend popular or complementary menu items from the MENU if asked.
    - Show details: Use the 'get_menu' tool (parameter 'category_ids' is optional) to look up menu items.
    - Preview order totals: Use the 'calculate_total' tool to compute and show order_details, subtotal, discounts_applied, and total_price. **calculate_total is read-only and must NOT save files.**
    - Ask for confirmation: After showing the preview, ask the customer whether they want to confirm the order.
    - Finalize the order: Only after the customer explicitly confirms (e.g. "yes", "confirm", "place order") call 'create_order' to save the order and return an order_id and created_at. Then thank the customer and direct them to the payment window.

    Always use only the MENU items (IDs from the MENU) when making totals.

    Here is the `MENU`:
    {MENU_DATA}
    """

    # 3) messages: 1-shot example that shows the preview -> confirmation -> create flow
    messages = [
        {"role": "system", "content": system_prompt},

        # 1-shot example starts
        {"role": "assistant", "content": greeting_prompt},
        {"role": "user", "content": "I want 2 Burgers please"},
        {"role": "assistant", "content": "We have Veggie Burger $5.49 and Cheeseburger $5.99. We are having 10% discount on Cheeseburger. What would you like?"},
        {"role": "user", "content": "2 cheeseburgers please"},
        {"role": "assistant", "content": "Ok, would you like some drinks? We are having 10% off on Coca-Cola and 20% off on Orange Juice."},
        {"role": "user", "content": "no"},

        # Assistant calls calculate_total for a preview (read-only)
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "calculate_total", "arguments": {"order": json.dumps([{"item_id": 1, "quantity": 2}])}}}
        ]},

        # Tool returns preview (no order_id yet)
        {"role": "tool", "name": "calculate_total", "content": json.dumps({
            "order_details": [
                {"item_id": 1, "name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98, "line_discount": 1.2}
            ],
            "subtotal": 11.98,
            "discounts_applied": [{"description": "10% off on Cheeseburger", "amount": -1.2}],
            "total_price": 10.78
        })},

        # Assistant shows preview and asks for confirmation
        {"role": "assistant", "content": "Here is your order preview: 2 x Cheeseburger. Subtotal $11.98, discounts applied $1.20, total $10.78. Would you like to confirm and place this order? (yes/no)"},

        # User confirms
        {"role": "user", "content": "Yes, please confirm"},

        # Assistant calls create_order to finalize (tool that saves)
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "create_order", "arguments": {"order": json.dumps([{"item_id": 1, "quantity": 2}])}}}
        ]},

        # Tool returns saved order metadata
        {"role": "tool", "name": "create_order", "content": json.dumps({
            "order_details": [
                {"item_id": 1, "name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98, "line_discount": 1.2}
            ],
            "subtotal": 11.98,
            "discounts_applied": [{"description": "10% off on Cheeseburger", "amount": -1.2}],
            "total_price": 10.78,
            "order_id": "example_order_id",
            "created_at": "2025-08-11T00:00:00",
            "saved_as": "orders/order_example_order_id.csv"
        })},

        # Assistant finalizes message
        {"role": "assistant", "content": "Great — your order was created with ID example_order_id: 2 Cheeseburgers. With 10% off, you pay $10.78. Thank you and please proceed to the payment window."}
        # 1-shot example ends
    ]
    # -----------------------------------------------------------------

    # Map function names to the actual functions for dispatch
    available_tools = {
        "get_menu": get_menu,
        "calculate_total": calculate_total,
        "create_order": create_order
    }


    print("-----------FastFood Restaurant-------------")
    print(f"assistant> {greeting_prompt}")
    messages.append({"role": "assistant", "content": greeting_prompt})

    while True:
        user_prompt = input('user> ')
        messages.append({"role": "user", "content": user_prompt})

        response = llama(messages=messages, tools=default_tools)
        print(json.dumps(response, indent=4))


        message = response["message"]
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
        
        