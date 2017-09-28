import requests
import urllib.parse
import json
import typing

def authenticate(root_url, serial, secret):
    payload = {'username': serial, 'password': secret}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(urllib.parse.urljoin(root_url, 'auth-token-obtain/'), data=json.dumps(payload), headers=headers)
    data = response.json()
    if 'token' in data:
        return data['token']
    else:
        return None
