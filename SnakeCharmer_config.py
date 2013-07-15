#!/usr/bin/python3
# SnakeCharmer_config.py

"""
This file contains configuration options for SnakeCharmer.py.
"""

HTTP_PORT  = 8000;
HTTPS_PORT = 8001;

HTTP_WEB_ADDRESS  = "192.168.0.135";
HTTPS_WEB_ADDRESS = HTTP_WEB_ADDRESS;

ONE_DAY = 24*60*60;  		# length of one day in seconds
cookie_expiration = ONE_DAY;    # expires values of HTML cookie
				# Note that the hashID associated with cookie
				# may expire sooner.

fpem = 'server.pem';
