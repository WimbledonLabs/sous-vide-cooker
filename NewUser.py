# This is not a good example: look elsewhere for an example.

import htpasswd;
import pstorage;
import os;
import sys;
import getpass;

if __name__ == '__main__':
    storage = pstorage.Storage( '127.0.0.1' );
    root_password = getpass.getpass( 'pstorage root password: ' );

    storage.login( 'root', root_password );

    sys.stdout.write( '           login: ' );
    sys.stdout.flush();
    login = sys.stdin.readline().strip();

    password = getpass.getpass( '        password: ' );
    password2 = getpass.getpass( 'password (again): ' );

    if password != password2:
        sys.stderr.write( "Passwords don't match!  Try again.\n" );
        sys.exit(0);

    magic, salt, code = htpasswd.md5crypt( password );
    password_bytes = magic + salt + b'$' + code;

    if os.path.exists("storserv_data/Server/Users/%s" % login):
        sys.stdout.write('User already exists, overwrite user? (y or n): ');
        sys.stdout.flush();
        newpass = sys.stdin.readline().strip();
        if newpass != 'y':
            exit();
        else:
            print("Changing password");
   
    storage.Server.Users[login] = storage.Object();
    storage.Server.Users[login].password = password_bytes;
