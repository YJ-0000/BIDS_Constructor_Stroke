import json
import glob
import os


def update_json_files(root_folder):
    """
    Searches recursively for JSON files matching the pattern:
      <root_folder>/.../func/sub-*task-rest_*_bold.json
    and adds (or updates) the key "TaskName" with value "rest".
    """
    # Build a recursive search pattern: look into any "func" folder under the root
    pattern = os.path.join(root_folder, '**', 'func', 'sub-*task-rest_*_bold.json')
    # for backup files
    # pattern = os.path.join(root_folder, '**', 'func','backup', 'sub-*task-rest_*_bold*.json')
    json_files = glob.glob(pattern, recursive=True)

    if not json_files:
        print("No matching JSON files found.")
        return

    for json_file in json_files:
        try:
            # Open and load the JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if the loaded JSON is a dictionary
            if isinstance(data, dict):
                data['TaskName'] = 'rest'
            else:
                print(f"Skipping {json_file}: JSON content is not an object.")
                continue

            # Write the updated JSON data back to the file with pretty-print formatting
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            print(f"Updated {json_file}")

        except Exception as e:
            print(f"Error processing {json_file}: {e}")


if __name__ == '__main__':
    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # Set the root BIDS folder
    root_bids_folder = config["data"]["output_path"]
    update_json_files(root_bids_folder)
