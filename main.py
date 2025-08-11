from fcall import *
import json

# --- Example usage (simple) ---
if __name__ == "__main__":
    sample_order = [{"item_id": 1, "quantity": 2}, {"item_id": 4, "quantity": 1}]
    preview = calculate_total(sample_order)
    print("Preview:", json.dumps(preview, indent=4))

    final = create_order(sample_order)
    print("Saved order:", json.dumps(final, indent=4))