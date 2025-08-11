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
        # {"discount_percentage": 0.05, "item_ids": [3]},
        {"discount_percentage": 0.20, "item_ids": [5]}
    ]
}
MENU_DATA = copy.deepcopy(data)

# The customer cart is stored globally for simplicity
cart = []

def add_or_update_cart_items(items):
    """
    Add new items to the cart or update quantities if they already exist.
    items: list of dicts, e.g. [{"item_id": 1, "quantity": 2}, ...]
    """
    global cart
    for new_item in items:
        for cart_item in cart:
            if cart_item["item_id"] == new_item["item_id"]:
                cart_item["quantity"] += new_item["quantity"]
                break
        else:
            cart.append({"item_id": new_item["item_id"], "quantity": new_item["quantity"]})


def remove_cart_items(item_ids):
    """
    Remove items from the cart by item_id.
    item_ids: list of integers, e.g. [1, 5]
    """
    global cart
    cart = [item for item in cart if item["item_id"] not in item_ids]


def set_cart_item_quantities(items):
    """
    Set new quantities for existing items in the cart.
    items: list of dicts, e.g. [{"item_id": 1, "quantity": 5}, ...]
    """
    global cart
    for change_item in items:
        for cart_item in cart:
            if cart_item["item_id"] == change_item["item_id"]:
                cart_item["quantity"] = change_item["quantity"]
                break

    

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
    # ----------------- Replace these five variables -----------------

    # 1) default_tools: explicit, non-ambiguous tool schema including cart ops
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
                "name": "add_or_update_cart_items",
                "description": "Add items to the current cart or increase quantity if item exists. Returns the updated cart. Items must include item_id and quantity (>0).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "description": "List of items to add or update in cart.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer"},
                                    "quantity": {"type": "integer", "minimum": 1}
                                },
                                "required": ["item_id", "quantity"]
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
                "name": "remove_cart_items",
                "description": "Remove one or more items from the cart by their item_id. Returns the updated cart.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "integer"},
                            "description": "List of item IDs to remove from the cart."
                        }
                    },
                    "required": ["item_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_cart_item_quantities",
                "description": "Set new quantities for existing items in the cart (replace). Returns the updated cart. Quantity must be >=1.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer"},
                                    "quantity": {"type": "integer", "minimum": 1}
                                },
                                "required": ["item_id", "quantity"]
                            },
                            "description": "List of item_id/quantity pairs to set in cart."
                        }
                    },
                    "required": ["items"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_total",
                "description": "Read-only preview: compute order_details, subtotal, discounts_applied and total_price for the provided order (list of item_id/quantity). Does NOT save files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "minItems": 1,
                            "description": "List of items to compute totals for (preview only).",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer"},
                                    "quantity": {"type": "integer", "minimum": 1}
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
                "description": "Save a confirmed order to CSV (using pandas) and return order_id, created_at and saved filename. **Do not call when cart is empty.** The order must have at least one item with quantity >= 1.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "array",
                            "minItems": 1,
                            "description": "Confirmed list of items to persist to disk. Must have at least 1 item, each with item_id and quantity >= 1.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_id": {"type": "integer"},
                                    "quantity": {"type": "integer", "minimum": 1}
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

    # 2) greeting_prompt and 3) system_prompt with cart instructions
    greeting_prompt = "Welcome! I'm here to take your order — what would you like to add to your cart today?"

    system_prompt = f"""
    You are a friendly and efficient fast-food restaurant receptionist that manages a customer cart and creates orders.
    Rules and behavior (follow exactly):
    - Use `get_menu` to show menu items when the user asks or when suggesting items.
    - Use `add_or_update_cart_items` when the user asks to add items or increase quantities (e.g. "add 2 cheeseburgers").
    - Use `remove_cart_items` when the user asks to remove items (e.g. "remove the Coke").
    - Use `set_cart_item_quantities` when the user explicitly wants to set exact quantities (e.g. "make cheeseburgers 3").
    - Use `calculate_total` to preview totals. Always preview before asking for confirmation.
    - NEVER call `create_order` unless the user explicitly confirms the final order (explicit confirmation examples: "yes", "confirm", "place order", "checkout now").
    - NEVER call `create_order` with an empty order. The order must contain at least one item (quantity >= 1).
    - When you call a tool, supply the appropriate arguments (do not leave required arguments empty).
    - After create_order returns, present the order_id and a polite thank-you and direct the customer to payment.

    When interacting with the user, be concise. Ask clarifying questions only when necessary (e.g., size/toppings) and show the cart preview when asked or before finalizing.
    Always use only MENU item IDs when constructing orders.
    """

    # 4) messages: 1-shot example showing add -> preview -> change -> preview -> confirm -> create flow
    messages = [
        {"role": "system", "content": system_prompt},

        # assistant greets
        {"role": "assistant", "content": greeting_prompt}

        # # user asks to add items
        # {"role": "user", "content": "I'd like 2 Cheeseburgers and 1 Orange Juice, please."},

        # # assistant calls add_or_update_cart_items
        # {"role": "assistant", "content": "", "tool_calls": [
        #     {"function": {"name": "add_or_update_cart_items", "arguments": {"items": json.dumps([{"item_id": 1, "quantity": 2}, {"item_id": 5, "quantity": 1}])}}}
        # ]},

        # # tool returns current cart (example)
        # {"role": "tool", "name": "add_or_update_cart_items", "content": json.dumps([
        #     {"item_id": 1, "quantity": 2},
        #     {"item_id": 5, "quantity": 1}
        # ])},

        # # assistant previews totals by calling calculate_total
        # {"role": "assistant", "content": "", "tool_calls": [
        #     {"function": {"name": "calculate_total", "arguments": {"order": json.dumps([{"item_id": 1, "quantity": 2}, {"item_id": 5, "quantity": 1}])}}}
        # ]},

        # # tool returns preview (no order_id)
        # {"role": "tool", "name": "calculate_total", "content": json.dumps({
        #     "order_details": [
        #         {"item_id": 1, "name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98, "line_discount": 1.2, "discount_pct": 0.1},
        #         {"item_id": 5, "name": "Orange Juice", "quantity": 1, "price_per_item": 1.99, "line_total": 1.99, "line_discount": 0.4, "discount_pct": 0.2}
        #     ],
        #     "subtotal": 13.97,
        #     "discounts_applied": [
        #         {"description": "10% off on Cheeseburger", "amount": -1.2},
        #         {"description": "20% off on Orange Juice", "amount": -0.4}
        #     ],
        #     "total_price": 12.37
        # })},

        # # assistant asks for confirmation
        # {"role": "assistant", "content": "Here is your preview: 2 x Cheeseburger, 1 x Orange Juice. Total $12.37 (discounts applied $1.60). Would you like to confirm and place this order? (yes/no)"},

        # # user changes mind and wants to remove Orange Juice, add Coca-Cola instead
        # {"role": "user", "content": "Please take out the Orange Juice and add 1 Coca-Cola instead."},

        # # assistant calls remove and add (tool calls)
        # {"role": "assistant", "content": "", "tool_calls": [
        #     {"function": {"name": "remove_cart_items", "arguments": {"item_ids": json.dumps([5])}}},
        #     {"function": {"name": "add_or_update_cart_items", "arguments": {"items": json.dumps([{"item_id": 4, "quantity": 1}])}}}
        # ]},

        # # tool returns current cart (example)
        # {"role": "tool", "name": "remove_cart_items", "content": json.dumps([{"item_id": 1, "quantity": 2}])},
        # {"role": "tool", "name": "add_or_update_cart_items", "content": json.dumps([{"item_id": 1, "quantity": 2}, {"item_id": 4, "quantity": 1}])},

        # # assistant previews totals again
        # {"role": "assistant", "content": "", "tool_calls": [
        #     {"function": {"name": "calculate_total", "arguments": {"order": json.dumps([{"item_id": 1, "quantity": 2}, {"item_id": 4, "quantity": 1}])}}}
        # ]},

        # # tool returns preview
        # {"role": "tool", "name": "calculate_total", "content": json.dumps({
        #     "order_details": [
        #         {"item_id": 1, "name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99, "line_total": 11.98, "line_discount": 1.2, "discount_pct": 0.1},
        #         {"item_id": 4, "name": "Coca-Cola", "quantity": 1, "price_per_item": 1.49, "line_total": 1.49, "line_discount": 0.15, "discount_pct": 0.1}
        #     ],
        #     "subtotal": 13.47,
        #     "discounts_applied": [
        #         {"description": "10% off on Cheeseburger", "amount": -1.2},
        #         {"description": "10% off on Coca-Cola", "amount": -0.15}
        #     ],
        #     "total_price": 12.12
        # })},

        # # assistant asks confirmation again and user confirms
        # {"role": "assistant", "content": "Preview: 2 x Cheeseburger, 1 x Coca-Cola. Total $12.12. Confirm and place order?"},
        # {"role": "user", "content": "Yes, place order please."},

        # # assistant calls create_order (finalize)
        # {"role": "assistant", "content": "", "tool_calls": [
        #     {"function": {"name": "create_order", "arguments": {"order": json.dumps([{"item_id": 1, "quantity": 2}, {"item_id": 4, "quantity": 1}])}}}
        # ]},

        # # tool returns saved order metadata (example)
        # {"role": "tool", "name": "create_order", "content": json.dumps({
        #     "order_details": [
        #         {"item_id": 1, "name": "Cheeseburger", "quantity": 2, "price_per_item": 5.99},
        #         {"item_id": 4, "name": "Coca-Cola", "quantity": 1, "price_per_item": 1.49}
        #     ],
        #     "subtotal": 13.47,
        #     "discounts_applied": [{"description": "10% off on Cheeseburger", "amount": -1.2}, {"description": "10% off on Coca-Cola", "amount": -0.15}],
        #     "total_price": 12.12,
        #     "order_id": "example_order_id",
        #     "created_at": "2025-08-11T00:00:00",
        #     "saved_as": "orders/order_example_order_id.csv"
        # })},

        # # assistant final message
        # {"role": "assistant", "content": "Great — your order was created with ID example_order_id. Thank you! Please proceed to the payment window."}
    ]
    # -----------------------------------------------------------------

    # Map function names to the actual functions for dispatch
    available_tools = {
        "get_menu": get_menu,
        "add_or_update_cart_items": add_or_update_cart_items,
        "remove_cart_items": remove_cart_items,
        "set_cart_item_quantities": set_cart_item_quantities,
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
            print(json.dumps(followup, indent=4))

            print_content(followup["message"])
            messages.append(followup["message"])
        else:
            print_content(message)
            messages.append(message)
        
        