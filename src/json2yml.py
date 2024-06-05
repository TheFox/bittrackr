#!/usr/bin/env python3

import json
import yaml
import sys

def json_to_yaml(json_file_path: str, yaml_file_path: str):
    # Read the JSON file
    with open(json_file_path, 'r') as json_file:
        json_data = json.load(json_file)

    # Convert JSON data to YAML format and write to the YAML file
    with open(yaml_file_path, 'w') as yaml_file:
        yaml.dump(json_data, yaml_file, default_flow_style=False, sort_keys=False)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python json2yml.py <input_json_file> <output_yaml_file>')
        sys.exit(1)

    json_file_path = sys.argv[1]
    yaml_file_path = sys.argv[2]

    json_to_yaml(json_file_path, yaml_file_path)
    print(f'-> json: {json_file_path}')
    print(f'-> yaml: {yaml_file_path}')

