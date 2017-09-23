import requests

def authenticate(root_url, serial, secret):
    response = requests.get(root_url + '/kits/1/', auth=(serial, secret))
    pass
