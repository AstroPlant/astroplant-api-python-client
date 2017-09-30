import json

def read_config():
    with open('./examples/client_config.json') as f:
        data = json.load(f)

    return data
