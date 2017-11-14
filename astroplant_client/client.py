import requests
from urllib.parse import urljoin
import datetime
import json
import websocket
import jwt

#: The number of seconds before token expiration when a refresh is required
REFRESH_BEFORE_EXPIRY_IN_SECONDS = 60.0

#: The number of seconds before token expiration where a refresh is still attempted
REFRESH_BEFORE_EXPIRY_CUTOFF_IN_SECONDS = 3.0

class AuthenticationError(Exception):
    pass

class TokenRefreshError(Exception):
    pass

class Client(object):
    """
    AstroPlant API Client class implementing methods to interact with the AstroPlant API.
    """

    def __init__(self, root_url, websocket_url):
        """
        :param root_url: The url of the root of the API.
        """
        self.root_url = root_url
        self.websocket_url = websocket_url

        self.ws = websocket.WebSocket()
        self.token = None
        self.token_data = None
        self.token_exp = None

        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def authentication_required(func):
        def wrapper(*args):
            self = args[0]
            if self._needs_reauthentication():
                self._reauthenticate()
            return func(*args)
        return wrapper

    @authentication_required
    def get(self, url):
        return self._get(url)

    @authentication_required
    def post(self, url, payload):
        return self._post(url, payload)

    def _get(self, url):
        return self.session.get(url)

    def _post(self, url, payload):
        """
        Make a post request to the specified url with the given payload.

        :param url: The url to make the post request to.
        :param payload: The payload as a dictionary.
        """

        return self.session.post(url, json.dumps(payload))

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
        data = result.json()

        if result.status_code == 200 and 'token' in data:
            self._process_token(data['token'])
        else:
            if 'non_field_errors' in data:
                raise AuthenticationError("API error: %s" % data['non_field_errors'])
            else:
                raise AuthenticationError("Could not authenticate.")

    def _refresh_authentication(self):
        """
        Refresh the authentication token.

        Raises an TokenRefreshError if it cannot refresh the token.
        """
        payload = {'token': token}
        result = self._post(urljoin(self.root_url, 'auth-token-verify/'), payload)
        data = result.json()

        if result.status_code == 200 and 'token' in result:
            self._process_token(result['token'])
        else: 
            if 'non_field_errors' in result:
                raise TokenRefreshError("API error: %s" % result['non_field_errors'])
            else:
                raise TokenRefreshError("Could not refresh authentication token.")

    def _reauthenticate(self):
        """
        Reauthenticate to the API.

        Attempts to refresh the authentication token,
        and falls back on username/password authentication
        if it cannot refresh.
        """
        if self._can_refresh():
            # Attempt to refresh
            try:
                self._refresh_authentication()
                return
            except:
                pass

        # If we cannot refresh, or refresh failed, reauthenticate
        self.authenticate(self.auth_serial, self.auth_secret)

    def _verify_token(self, token):
        """
        Verifies a token on the API.

        :param token: The token to verify.
        :return: A boolean indicating whether the token is valid.
        """
        payload = {'token': token}
        result = self._post(urljoin(self.root_url, 'auth-token-verify/'), payload)
        return result.status_code == 200

    def _process_token(self, token):
        """
        Processes a JWT token.

        :param token: The JWT token.
        """
        self.token = token
        self.token_data = jwt.decode(self.token, verify = False)
        self.token_exp = datetime.datetime.fromtimestamp(int(self.token_data['exp']))
        self.session.headers.update({'Authorization': 'JWT %s' % self.token})

    def _needs_reauthentication(self):
        """
        Test whether the client requires reauthentication.

        :return: Boolean indicating whether the client needs to reauthenticate.
        """
        
        diff = self.token_exp - datetime.datetime.now()
        return diff.seconds < REFRESH_BEFORE_EXPIRY_IN_SECONDS

    def _can_refresh(self):
        """
        Test whether the client can refresh the current token.

        :return: Boolean indicating whether the client can refresh the current token.
        """

        diff = self.token_exp - datetime.datetime.now()
        return diff.seconds > REFRESH_BEFORE_EXPIRY_CUTOFF_IN_SECONDS

    def is_authenticated(self, verify = False):
        """
        Test whether the client is authenticated.

        :param verify: Verifies the authentication state with the API.
        :return: Boolean indicating whether the client is authenticated.
        """

        if not verify:
            diff = self.token_exp - datetime.datetime.now()
            return diff.seconds > 0
        else:
            return self._verify_token(self.token)

    def _open_websocket(self):
        self.ws.connect(self.websocket_url + "?token=%s" % self.token)

    def publish_measurement(self, sensor, value):
        """
        Publish a measurement over websockets.

        :param sensor: The sensor to send the measurement for.
        :param value: The value to send.
        """

        message = {
            'stream': 'measurements-publish',
            'payload': {
                'action': 'publish',
                'measurement': {
                    'sensor_type': sensor,
                    'date_time': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'value': value
                }
            }
        }

        self.ws.send(json.dumps(message))
