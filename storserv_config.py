#!/usr/bin/python3
# storserv_config.py

"""
This file contains configuration options for storserv.py.

"""

import os;
import sys;
import string;

#PROFILE_FILE = '/tmp/server-profile';		
	# Set to false or None if not required
PROFILE_FILE = None;


# NAMES OF STRING CONSTANTS:
#   *_PATH full unix path starting with /
RUN_PATH         = "/var/run/storserv";
SOCKET_PATH      = os.path.join(RUN_PATH,"storserv.socket");
PID_FILE         = os.path.join(RUN_PATH,"storserv.pid");

DATA_PATH        = "/home/stephen/sous-vide/storserv_data";

USERNAME         = "pstorage";
MAX_MESSAGE_SIZE = 32768;

EOT              = chr(4);

SESSION_INACTIVITY = 3600;	# one hour

# Unix paths relative to DATA_PATH
SERVER_OBJECT    = 'Server';
SERVER_RPATH     = 'Server';

SESSIONS_OBJECT  = '.'.join( (SERVER_OBJECT, "Sessions") );
SESSIONS_RPATH   = os.path.join( SERVER_OBJECT, "Sessions" );

USERS_OBJECT     = '.'.join( (SERVER_OBJECT, "Users") );
USERS_RPATH      = os.path.join( SERVER_OBJECT, "Users" );

ROLES_OBJECT     = "Roles";

DEFAULT_ROLES_LIST    = '.'.join( (SERVER_OBJECT, "default_roles") );
DEFAULT_ROLES_RPATH   = os.path.join( SERVER_OBJECT, "default_roles" );

# this is relative to any path
PERMISSIONS      = "Permissions";

# this is relative to a user path
PASSWORD  = "password";
