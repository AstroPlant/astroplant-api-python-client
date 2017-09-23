import json

import sys
import samples.config
import apiclient.auth

def main(argv):
    # Read configuration file
    conf = samples.config.read_config()

    # Authenticate
    apiclient.auth.authenticate(conf['api']['root'], conf['auth']['serial'], conf['auth']['secret'])

if __name__ == '__main__':
    main(sys.argv)
