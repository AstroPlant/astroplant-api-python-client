import json

def read_config():
    with open('./samples/client_config.json') as f:
        data = json.load(f)

    return data
