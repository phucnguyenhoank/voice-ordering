import uuid
from utils2 import llama # Assuming 'utils2.llama' is your LLM call function
import copy
import json
import ast
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
# -------------------------
# Helper: Safe parsing
# -------------------------
def safe_parse_items(raw_items):
    """
    Convert raw input from LLM to a valid list of {'item_id': int, 'quantity': int}.
    Repairs common mistakes like stringified lists or missing quantity.
    """
    # Step 1: Already a list?
    if isinstance(raw_items, list):
        return _filter_items(raw_items)

    # Step 2: String → try JSON
    if isinstance(raw_items, str):
        try:
            parsed = json.loads(raw_items)
            return _filter_items(parsed)
        except json.JSONDecodeError:
            pass

        # Step 3: String → try Python literal syntax
        try:
            parsed = ast.literal_eval(raw_items)
            return _filter_items(parsed)
        except Exception:
            pass

    # Step 4: Nothing worked → empty list
    return []


def _filter_items(items):
    """Ensure list contains only valid {'item_id': int, 'quantity': int} entries."""
    valid = []
    if isinstance(items, list):
        for item in items:
            # Full dict case
            if (isinstance(item, dict) and
                isinstance(item.get("item_id"), int) and
                isinstance(item.get("quantity"), int) and
                item["quantity"] >= 1):
                valid.append(item)

            # Repair case: int item_id only → assume quantity=1
            elif isinstance(item, int):
                valid.append({"item_id": item, "quantity": 1})

    return valid


# -------------------------
# Cart storage (example)
# -------------------------
customer_cart = []  # [{item_id, quantity}, ...]


# -------------------------
# Cart functions
# -------------------------
def add_or_increase_cart_items(items):
    """
    Add items to the cart or increase their quantity if they already exist.
    raw_items can be:
      - list of dicts: [{"item_id": 1, "quantity": 2}]
      - list of ints: [1, 2] (auto quantity=1)
      - JSON/Python string: "[{'item_id': 1, 'quantity': 2}]"
    """
    items = safe_parse_items(items)
    if not items:
        return {"error": "No valid items provided."}

    global customer_cart
    for new_item in items:
        found = False
        for cart_item in customer_cart:
            if cart_item["item_id"] == new_item["item_id"]:
                cart_item["quantity"] += new_item["quantity"]
                found = True
                break
        if not found:
            customer_cart.append(new_item)
    
    return {"message": "Items added/updated successfully.", "cart": customer_cart}


def remove_cart_items(item_ids):
    """
    Remove items from the cart by their IDs.
    raw_item_ids can be:
      - list of ints: [1, 2]
      - list of dicts: [{"item_id": 1}, {"item_id": 2}]
      - JSON/Python string
    """
    ids = _extract_ids(item_ids)
    if not ids:
        return {"error": "No valid item IDs provided."}

    global customer_cart
    customer_cart = [item for item in customer_cart if item["item_id"] not in ids]

    return {"message": "Items removed successfully.", "cart": customer_cart}


def set_cart_item_quantities(items):
    """
    Set exact quantities for items in the cart (replace, not add).
    If quantity is 0 or less → item is removed.
    """
    items = safe_parse_items(items)
    if not items:
        return {"error": "No valid items provided."}

    global customer_cart
    cart_dict = {item["item_id"]: item["quantity"] for item in customer_cart}

    for new_item in items:
        if new_item["quantity"] <= 0:
            cart_dict.pop(new_item["item_id"], None)
        else:
            cart_dict[new_item["item_id"]] = new_item["quantity"]

    customer_cart = [{"item_id": k, "quantity": v} for k, v in cart_dict.items()]

    return {"message": "Item quantities updated.", "cart": customer_cart}


# -------------------------
# Helper: ID extraction
# -------------------------
def _extract_ids(raw_ids):
    """Extract integer IDs from various formats."""
    if isinstance(raw_ids, list):
        ids = []
        for entry in raw_ids:
            if isinstance(entry, int):
                ids.append(entry)
            elif isinstance(entry, dict) and isinstance(entry.get("item_id"), int):
                ids.append(entry["item_id"])
        return ids

    if isinstance(raw_ids, str):
        try:
            parsed = json.loads(raw_ids)
            return _extract_ids(parsed)
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(raw_ids)
            return _extract_ids(parsed)
        except Exception:
            pass

    return []
    

def _load_order(order):
    """Accept list or JSON string and return list of dicts."""
    if isinstance(order, str):
        return json.loads(order)
    return order

def _get_item(item_id):
    return next(i for i in MENU_DATA["items"] if i["id"] == item_id)

def _get_item_discount(item_id):
    return next((d["discount_percentage"] for d in MENU_DATA["discounts"] if item_id in d["item_ids"]), 0.0)

def calculate_total():
    """
    Read-only preview using the global `cart`.
    Returns: dict with order_details, subtotal, discounts_applied, total_price
    """
    global cart
    # ensure cart is a list of dicts (keeps compatibility if cart was serialized)
    cart = _load_order(cart)

    subtotal = 0.0
    total = 0.0
    order_details = []
    discounts_applied = []

    for ord_item in cart:
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
        "total_price": total,
        "cart": cart  # return current cart for convenience
    }

def create_order(saved_folder="orders"):
    """
    Finalize & save order using pandas. Uses global cart.
    Returns order metadata + same totals. Clears cart after saving.
    """
    global cart
    cart = _load_order(cart)

    # guard: don't create empty orders
    if not cart:
        return {"error": "Cart is empty. Cannot create order."}

    totals = calculate_total()

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

    # Clear the cart after successful save
    cart = []

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
                "name": "add_or_increase_cart_items",
                "description": "Add items to the current cart or increase quantity if item exists. Returns the updated cart. Items must include item_id and quantity (>0).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "description": "List of items to add or increase in cart.",
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
                "description": "Read-only preview: compute order_details, subtotal, discounts_applied and total_price using the current global cart. Does NOT save files.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "Save a confirmed order (the current global cart) and return order_id, created_at and saved filename.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

    available_tools = {
        "get_menu": get_menu,
        "add_or_increase_cart_items": add_or_increase_cart_items,
        "remove_cart_items": remove_cart_items,
        "set_cart_item_quantities": set_cart_item_quantities,
        "calculate_total": calculate_total,
        "create_order": create_order
    }

    system_prompt = """
    You are a friendly, efficient fast-food restaurant receptionist who talks with customers through voice.
    You manage customer carts and create orders.
    You always inform to customers what you have done with their cart.
    When speaking to customers, never mention item IDs, use item names instead.
    Ask clarifying questions when needed (e.g., size, toppings).
    Always preview the cart before create an order.

    - Menu & Ordering Rules:
    1. Use `get_menu` tool to show or suggest menu items or a category of items and current available discounts to customers.
    2. Use `add_or_increase_cart_items` tool when adding new items or increasing existing quantities.
    3. Use `remove_cart_items` when removing specific items from the user cart.
    4. Use `set_cart_item_quantities` when setting exact item quantities.
    5. Use `calculate_total` to preview the order total, ALWAYS preview the order before asking for confirmation.
    6. Only call `create_order` after explicit customer confirmation (e.g., "yes", "confirm", "place order", "checkout now").
    7. Never call `create_order` with an empty cart, in this case, ask the customer again.
    8. When calling any tool, always pass all required arguments, never leave them empty.

    - After Order Placement:
    -- Once `create_order` returns, present the final total, thank the customer politely, and direct them to payment.
    -- End the conversation after payment instructions.
    
    - Here is the MENU:
    {MENU_DATA}
    """


    greeting_prompt = "Welcome! I'm here to take your order — what would you like to eat today?"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": greeting_prompt}
    ]


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
                # Deep copy so we don't mutate the original
                temp = copy.deepcopy(messages[-1])

                # Parse content so it's a nested object, not a string
                temp["content"] = json.loads(temp["content"])

                # Now pretty-print
                print(json.dumps(temp, indent=4, ensure_ascii=False))

            followup = llama(messages=messages, tools=default_tools)
            print(json.dumps(followup, indent=4))

            print_content(followup["message"])
            messages.append(followup["message"])
        else:
            print_content(message)
            messages.append(message)
        
        