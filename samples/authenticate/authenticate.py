import json

import sys
import samples.config
import apiclient

def main(argv):
    # Read configuration file
    conf = samples.config.read_config()

    # Set up client
    client = apiclient.Client(conf['api']['root'])

    # Authenticate
    client.authenticate(conf['auth']['serial'], conf['auth']['secret'])

    pass

if __name__ == '__main__':
    main(sys.argv)
