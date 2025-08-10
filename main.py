from fcall import get_menu
def calculate_total(items: list[dict]):
    print(items)
    for item_order in items:
        print(item_order)

arguments = {
                        "items": "[{\"name\": \"Coke\", \"quantity\": 2}]"
                    }
calculate_total(**arguments)