import json

# Replace with your actual JSON file name
json_filename = "evo_625_pressure_map.json"
# The name of the file you want to create
output_filename = "unoccupied_slots.txt"

with open(json_filename, 'r') as f:
    data = json.load(f)

# This list will hold the names of the vacant slots
unoccupied_slots = []

# Assuming the JSON is a dictionary of slots
for slot_name, values in data.items():
    # Dig into the profile to find is_occupied
    if "profile" in values and "is_occupied" in values["profile"]:
        if values["profile"]["is_occupied"] is False:
            unoccupied_slots.append(slot_name)

# Save the list to a text file
with open(output_filename, 'w') as f:
    for slot in unoccupied_slots:
        f.write(slot + '\n')

print(f"List of {len(unoccupied_slots)} unoccupied slots saved to {output_filename}")

