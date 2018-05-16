import requests
from urllib.parse import urljoin
import datetime
import json
import websocket
import jwt
from . import path

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
        self.ws_nonce = 0
        self.token = None
        self.token_data = None
        self.token_exp = None

        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        self.configuration_path = path.ConfigurationPath(self)

    def authentication_required(func):
        """
        Decorator to enforce the client is authenticated.

        :param func: The function to wrap.
        """

        def wrapper(*args):
            self = args[0]
            if self._needs_reauthentication():
                self._reauthenticate()
            return func(*args)
        return wrapper

    @authentication_required
    def get(self, relative_url):
        """
        Make a get request to the specified relative url.

        :param relative_url: The url relative to the root url to make the get request to.
        """

        response = self._get(self.root_url + relative_url)
        if response.text:
            response.body = json.loads(response.text)
        return response

    @authentication_required
    def post(self, relative_url, payload):
        """
        Make a post request to the specified relative url with the given payload.

        :param url: The url relative to the root url to make the post request to.
        :param payload: The payload as a dictionary.
        """

        response = self._post(self.root_url + relative_url, payload)
        if response.text:
            response.body = json.loads(response.text)
        return response

    def _get(self, url):
        """
        Make a get request to the specified url.

        :param url: The url to make the get request to.
        """
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
        url = (self.websocket_url + "kit/?token=%s") % self.token
        self.ws.connect(url)

    def publish_measurement(self, measurement):
        """
        Publish a measurement over websockets.

        :param sensor: The sensor to send the measurement for.
        :param value: The value to send.
        """

        message = {
            'stream': 'publish-measurement',
            'nonce': self.ws_nonce,
            'payload': {
                'action': 'publish',
                'measurement_type': measurement.get_measurement_type(),
                'measurement': {
                    'peripheral': measurement.get_peripheral().get_name(),
                    'physical_quantity': measurement.get_physical_quantity(),
                    'physical_unit': measurement.get_physical_unit(),
                    'date_time': measurement.get_date_time().isoformat() + 'Z',
                    'value': measurement.get_value()
                }
            }
        }
        
        self.ws_nonce += 1

        self.ws.send(json.dumps(message))
