import json

import sys
import samples.config
import apiclient

def main(argv):
    # Read configuration file
    conf = samples.config.read_config()

    # Set up client
    client = apiclient.Client(conf['api']['root'], conf['websockets']['url'])

    # Test whether the client is authenticated
    print("Client is authenticated: %s" % client.is_authenticated(verify = True))

    # Authenticate
    print("Authenticating...")
    client.authenticate(conf['auth']['serial'], conf['auth']['secret'])

    # Test authentication
    print("Client is authenticated: %s" % client.is_authenticated(verify = True))
    client._open_websocket()
    client.publish_measurement(1, 6.39)

if __name__ == '__main__':
    main(sys.argv)
