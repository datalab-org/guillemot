import json
from pathlib import Path


def load_opxrd_entry(entry_number: int, db_path: str):
    # load entry number <entry_number>.json as a pattern
    # Create the path to the requested JSON entry
    json_path = Path(db_path) / f"{entry_number}.json"

    # Open the JSON file in read-only mode
    with open(json_path, "r") as file:
        # Load the JSON contents as a Python object
        pattern = json.load(file)

    # Return the loaded pattern
    return pattern
