#!/usr/bin/python3

# This module provides support to interact with apache's htpasswd files.
# It is based on a modification made by S.C. Kremer to a recipe by M.
# Johnston's port of P-H. Kamp's hash routine as found in FreeBSD 2.
#

# Based on FreeBSD src/lib/libcrypt/crypt.c 1.2
# http://www.freebsd.org/cgi/cvsweb.cgi/~checkout~/src/lib/libcrypt/crypt.c?rev=1.2&content-type=text/plain

# Original license:
# * "THE BEER-WARE LICENSE" (Revision 42):
# * <phk@login.dknet.dk> wrote this file.  As long as you retain this notice you
# * can do whatever you want with this stuff. If we meet some day, and you think
# * this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp

# This port adds no further stipulations.  I forfeit any copyright interest.
# (M. Johnston?)

# I have updated the code to use hashlib instead of md5.  Removed some of the
# testing rountines and added some to interact directly with the htpasswd file.
# I have also added superfluous semi-colons to the ends of all lines.
# -S. Kremer, 2010

import sys;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);


import hashlib;
import getpass;
import os;
import fcntl;
from functools import reduce


itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

def make_salt():
  return bytes( reduce( lambda x,y:x+y, 
                 [ itoa64[ i&63 ] for i in os.urandom(8) ],
               ), 'UTF-8' );


class HTPasswdFile:
  def __init__( this, path ):
    this.path = path;

  def __getitem__( this, key ):
    if type(key) == type(''):
      key = bytes( key, 'UTF-8' );
    fp = open( this.path, 'rb' );
    while 1:
      line = fp.readline().strip();
      login, code = line.split(b':');
      if key==login:
        fp.close();
        return HTPasswdEntry( login, code );
    fp.close();
    raise KeyError(login);

  def __setitem__( this, key, value ):
    fp = open( this.path );
    lines = fp.readlines();
    fp.close();

    fp = open( this.path, 'w' );
    fd = fp.fileno();

    fcntl.flock( fd, fcntl.LOCK_EX);
    found = 0;

    for line in lines:
      login, code = line.split(':');
      if key!=login:
        fp.write( line );

    if value!=this.__delitem__:	
	# if the value is set to the delete function
        # don't  insert the value (this is used as a special sentinel value)
      md5parts = md5crypt( value );
      md5string = md5parts[0] + md5parts[1] + b'$' + md5parts[2];
      fp.write( key + ':' + md5string.decode('UTF-8') + '\n' );
      fcntl.flock( fd, fcntl.LOCK_UN);
      fp.close();

  def __delitem__( this, key ):
    this[key] = this.__delitem__;	# insert the special sentinel value


class HTPasswdEntry:
  def __init__( this, login, code ):
    """
    code is of the format $apr1$xxxxxxxx$xxxxxxxxxxxxxxxxxxxxxx
    """
    if type(login)==type(''):
      this.login = bytes(login,'UTF-8');

    this.magic, this.salt, this.crypt = code[1:].split(b'$');
	# ingnore leading $ and trailing NL

  def __repr__( this ):
    return ( this.login + b':$' + this.magic + b'$' + this.salt + b'$' + this.crypt ).decode( 'UTF-8' );

  def __eq__( this, password ):
    """
    Check if the provided password matches the encrypted password associated
    with this HTPasswdEntry.
    """
    provided = md5crypt( password, this.salt, b'$'+this.magic+b'$' )[2];
    sys.stderr.write( '%s %s\n' % (provided,this.crypt) );
    return provided == this.crypt;

def md5crypt(password, salt=None, magic=b'$apr1$'):
    # /* The password first, since that is what is most unknown */ 
    # /* Then our magic string */ 
    # /* Then the raw salt */

    if type(password)==type(""):
      password = bytes( password, 'UTF-8' );
    if not salt:
      salt = make_salt();
    elif type(salt)==type(""):
      salt = bytes( salt, 'UTF-8' );

    m = hashlib.md5();
    m.update( password + magic + salt );

    # /* Then just as many characters of the MD5(pw,salt,pw) */
    mixin = hashlib.md5(password + salt + password).digest();
    for i in range(0, len(password)):
      m.update( bytes(mixin[i % 16:i%16+1]) );

    # /* Then something really weird... */
    # Also really broken, as far as I can tell.  -m
    i = len(password)
    while i:
        if i & 1:
            m.update(b'\x00')
        else:
            m.update(password[0:1]);
        i >>= 1;

    final = m.digest()

    # /* and now, just to make sure things don't run too fast */
    for i in range(1000):
        m2 = hashlib.md5()
        if i & 1:
            m2.update(password)
        else:
            m2.update(final)

        if i % 3:
            m2.update(salt)

        if i % 7:
            m2.update(password)

        if i & 1:
            m2.update(final)
        else:
            m2.update(password)

        final = m2.digest()

    # This is the bit that uses to64() in the original code.


    rearranged = '';
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
      v = final[a] << 16 | final[b] << 8 | final[c];
      for i in range(4):
        rearranged += itoa64[v & 0x3f]; 
        v >>= 6;

    v = final[11];
    for i in range(2):
        rearranged += itoa64[v & 0x3f]; v >>= 6;

    rearranged = bytes( rearranged, 'UTF-8' );
    #return magic + salt + '$' + rearranged
    return magic, salt, rearranged;

def mkpasswd():
  import sys;
  import getpass;

  sys.stdout.write( '           login: ' );
  sys.stdout.flush();
  login = sys.stdin.readline().strip();

  password = getpass.getpass( '        password: ' );
  password2 = getpass.getpass( 'password (again): ' );

  if password != password2:
    sys.stderr.write( "Passwords don't match!  Try again.\n" );
    sys.exit(0);

  md5parts = md5crypt( password );
  md5string = md5parts[0] + md5parts[1] + b'$' + md5parts[2];
  entry = HTPasswdEntry( login, md5string );
  print("Please send the following string in an e-mail to Dr. Kremer:\n");
  print(entry);
  print() ;

def filetest():
  passwd=HTPasswdFile('/tmp/dav_svn.passwd');

  # add entry
  passwd['tester'] = b'secret';
  print( "passwd['tester'] = 'secret'" );

    # validate password
  print( "passwd['tester']=='secret';", passwd['tester']=='secret' );
  print( "passwd['tester']=='invalid';", passwd['tester']=='invalid' );

    # change entry
  passwd['tester']=b'newpass';
  print( "passwd['tester']='newpass';" );

    # validate password
  print( "passwd['tester']=='secret';", passwd['tester']=='secret' );
  print( "passwd['tester']=='newpass';", passwd['tester']=='newpass' );

    # delete password
  del passwd['tester'];
  print( "del passwd['tester'];" );

def validate():
  import sys;
  import getpass;

  sys.stdout.write( '           login: ' );
  sys.stdout.flush();
  login = sys.stdin.readline().strip();

  sys.stdout.write( '            salt: ' );
  sys.stdout.flush();
  salt = sys.stdin.readline().strip();

  password = getpass.getpass( '        password: ' );

  md5parts = md5crypt( password, salt );
  md5string = md5parts[0] + md5parts[1] + b'$' + md5parts[2];
  entry = HTPasswdEntry( login, md5string );
  print(entry);
  
  
if __name__ == '__main__':
  #mkpasswd();
  #filetest();
  validate();
