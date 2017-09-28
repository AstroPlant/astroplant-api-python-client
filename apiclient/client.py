import requests
from urllib.parse import urljoin
import json
import jwt

class AuthenticationError(Exception):
    pass

class Client(object):
    """
    AstroPlant API Client class implementing methods to interact with the AstroPlant API.
    """

    def __init__(self, root_url):
        """
        :param root_url: The url of the root of the API.
        """
        self.root_url = root_url
        self.authenticated = False

        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def _post(self, url, payload):
        """
        Make a post request to the specified url with the given payload.

        :param url: The url to make the post request to.
        :param payload: The payload as a dictionary.
        """

        return self.session.post(url, json.dumps(payload)).json()

    def authenticate(self, serial, secret):
        """
        Authenticates the client using a serial and secret.
        Stores the serial and secret so the client can
        re-authenticate when it needs to.

        :param serial: The serial of the kit.
        :param secret: The kit secret.
        """

        self.auth_serial = serial
        self.auth_secret = secret

        payload = {'username': serial, 'password': secret}
        result = self._post(urljoin(self.root_url, 'auth-token-obtain/'), payload)

        if 'token' in result:
            self.token = result['token']
            self.token_data = jwt.decode(self.token, verify = False)
        else:
            if 'non_field_errors' in result:
                raise AuthenticationError("API error: %s" % result['non_field_errors'])
            else:
                raise AuthenticationError("Could not authenticate.")
