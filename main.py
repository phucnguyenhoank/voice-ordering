from fcall import *
import json

# Get full menu (no filtering)
full_menu = get_menu()
print(json.dumps(full_menu, indent=4))

print('-----------')
# Get menu for only "Burgers" and "Drinks"
filtered_menu = get_menu(categories=["Burgers", "drinks"])
print(json.dumps(filtered_menu, indent=4))