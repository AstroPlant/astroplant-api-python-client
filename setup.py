#!/usr/bin/env python

from distutils.core import setup

setup(name='astroplant-client',
      version='0.1',
      description='AstroPlant API client',
      author='AstroPlant',
      author_email='thomas@kepow.org',
      url='https://astroplant.io',
      packages=['astroplant_client'],
	  install_requires=['requests', 'pyjwt', 'websocket-client']
     )

