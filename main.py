from fcall import *
import json

# --- Example usage (simple) ---
if __name__ == "__main__":
    # json.dumps()
    raw_items = r"[{'item_id': 4, 'quantity': 2}]"
    out = safe_parse_items(raw_items)
    print(out)
    print(type(out))