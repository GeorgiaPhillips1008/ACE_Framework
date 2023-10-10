import json


def parse_json(input_string):
    try:
        return json.loads(input_string)
    except json.JSONDecodeError:
        return None
