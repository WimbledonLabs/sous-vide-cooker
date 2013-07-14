#!/usr/bin/python3
# storserv.py
# storage server

"""
This file provides a server that responds to pstorage requests via a
unix domain socket.  It interprets those requests to interact with
a portion of the file system (unlike previous versions which used an SQL
database).
"""

import sys;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);

import os;
import re;
import pwd;
import math;
import time;
import glob;
import string;
import socket;
import shutil;
import marshal;
import hashlib;
import htpasswd;
import traceback;
import mimetypes;

# configuration options are found here:
import storserv_config;
from functools import reduce

################################################################################
# SVN Info
################################################################################

svn_regex = re.compile( r'^\$[^:]*: (.*) \$$' );

SVN_INFO = {
  'Date': """$Date: 2012-02-27 08:08:43 -0500 (Mon, 27 Feb 2012) $""",
  'Revision': """$Revision: 3372 $""",
  'Author': """$Author: skremer $""",
  'HeadURL': """$HeadURL: https://www.kremer.ca/svn/Repository/Projects/SnakeCharmer/6.0/storserv.py $""",
  'Id': """$Id: storserv.py 3372 2012-02-27 13:08:43Z skremer $""",
  };

for key in SVN_INFO:
  SVN_INFO[ key ] = svn_regex.match( SVN_INFO[ key ] ).group(1);

# Note you must give the command:
#  svn propset svn:keywords "Date Revision Author HeadURL Id" storserv.py
# for this to work.

################################################################################
################################################################################
################################################################################
# constants
################################################################################
################################################################################
################################################################################

# characters used in hash-codes and salts
# this is a string of 26+26+12 = 64 printable characters that can be used 
# for encoding any 6 bit integer
itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

# now produce an array which maps arbitrary bytes to values from the string
# above
a64converter = {};
for i in range(0,256):
  a64converter[ i ] = itoa64[ i//4 ];




################################################################################
################################################################################
################################################################################
# some untility functions
################################################################################
################################################################################
################################################################################

def pptraceback(): 
  """
  Generate a text string containing the lastest exception.

  This is used to send an error message back to the client over a network
  (text connection).
  """
  return reduce( lambda x,y: x+y, \
                 traceback.format_exception(*(sys.exc_info())) );

################################################################################

def write_exception():
  """
  This function writes an error message to the stderr of this program
  (normally redirected to a file in /var/log).
  """

  sys.stderr.write( 80*"*" + "\n" );
  sys.stderr.write( reduce( lambda x,y: x+y, traceback.format_exception(*(sys.exc_info())) ) );
  sys.stderr.write( 80*"*" + "\n" );

################################################################################

def make_salt(length=8):
  """
  Generate a cryptographically random string of length=length printable 
  charcters selected from the global constant itoa64.

  This operates by generating a cryptographically random string.
  """

  # this implementation should be fairly efficient because it uses only
  # 1 function call and 1 implied loop
  return ''.join( [ a64converter[i] for i in os.urandom(length) ] );

  # old implementation
  #return reduce( lambda x,y:x+y, 
  #               [ itoa64[ ord(i)&63 ] for i in os.urandom(length) ] );

################################################################################

def crypt( sessIP, sessID, salt=None, older=0 ):
  """
  Return an encrypted version of the session IP and session ID, mashed
  with a serverside key and a timestamp.

  sessIP is a string containing an IPV(4/6) address.
  sessID in an integer.

  The timestep has a granularity equal to the global constant,
  SESSION_INACTIVITY, measured in seconds.
  """

  if salt:	# if a salt value is provided, use it
    salt = salt[0:8];  # use first 8 characters as salt
  else:		# otherwise make up some salt
    salt = make_salt();

  timestamp = int( time.time() / storserv_config.SESSION_INACTIVITY );

  if older:	# check if older argument flag is set
    timestamp -= older;	# use an older timestamp

  # generates a hashword from the sessIP + sessID + salt + server_key + 
  # timestamp - this is designed to be hard to fake for the given data

  # attach the salt to the front of the returned hash

  # code_string = sessIP + ' ' + str(sessID) + ' ' + salt + ' ' + server_key + ' ' + str(timestamp);

  return salt+str( hashlib.md5( bytes( sessIP + str(sessID) + salt + \
                                         server_key + str(timestamp), \
                                       'UTF-8' \
                                     ) \
                              ).hexdigest() );

MARSHAL_SENTINEL = b'marshalled/python';
MARSHALLED_PYTHON_OFFSET = len( MARSHAL_SENTINEL );

################################################################################

def path2value( path ):
  """
  Return a string that can be evaluated based on what is stored at the given 
  path.
  """
  full_path = os.path.join( storserv_config.DATA_PATH, path );
  if os.path.isdir(full_path):
    if os.path.exists( os.path.join( full_path, '.object' ) ):
      return Object(path);
    elif os.path.exists( os.path.join( full_path, '.list' ) ):
      return List(path);
    elif os.path.exists( os.path.join( full_path, '.method' ) ):
      return Method(path);
    else:
      return Dict(path);

  else:
    fp = open( full_path, 'rb' );
    sentinel=fp.read( MARSHALLED_PYTHON_OFFSET );
    if sentinel == MARSHAL_SENTINEL:
      data = fp.read();

      if data[0]==ord('t'):	# convert python2 to python3 strings
        data = b'u' + data[1:];
      value = marshal.loads( data );
    else:
      fp.seek(0);
      value = File( fp.read(), mimetypes.guess_type( full_path ) );
    fp.close();

    return value;


################################################################################

def key2path( item_name ):
  if not type(item_name)==type(""):
    item_name = repr( item_name );
  item_name.replace('/',r'\x2');
  return item_name;

################################################################################


def empty_file( path ):
  """
  """
  fp = open( path, 'wb' );
  fp.close();  

################################################################################

def value2path( value, path ):
  """
  Write the given value at the location of path.
  """

  full_path = os.path.join( storserv_config.DATA_PATH, path );

  if os.path.exists( full_path ):
    if os.path.islink( full_path ):
      os.unlink( full_path );
    elif os.path.isdir( full_path ):
      shutil.rmtree( full_path );

  if isinstance(value,Object):
    if value.key==None or value.key==path:	# new object, create it
      os.mkdir( full_path );
      empty_file( os.path.join( full_path, '.object' ) );
    else:
      os.symlink( os.path.join( storserv_config.DATA_PATH, value.key), 
                  full_path );

  elif isinstance(value,Dict):
    if value.key==None or value.key==path:	# new object, create it
      os.mkdir( full_path );
    else:
      os.symlink( os.path.join( storserv_config.DATA_PATH, value.key), 
                  full_path );

  elif isinstance(value,List):
    if value.key==None or value.key==path:	# new object, create it
      os.mkdir( full_path );
      empty_file( os.path.join( full_path, '.list' ) );
      value2path( 0, os.path.join( full_path, '__len__' ) );
    else:
      os.symlink( os.path.join( storserv_config.DATA_PATH, value.key), 
                  full_path );

  elif isinstance(value,Method):
    if value.key==None or value.key==path:	# new object, create it
      os.mkdir( full_path );
      empty_file( os.path.join( full_path, '.method' ) );
    else:
      os.symlink( os.path.join( storserv_config.DATA_PATH, value.key), 
                  full_path );

  elif isinstance(value,File):
    fp = open( full_path, 'wb' );
    fp.write( value.content );
    fp.close();

  elif value in [Object,Dict,List,Method]:
    raise Exception("BAH!");

  else:
    fp = open( full_path, 'wb' );
    fp.write( MARSHAL_SENTINEL );
    fp.write( marshal.dumps( value ) );
    fp.close();

  return value;

################################################################################

def increment( variable ):
  """
  Increment the value of an integer variable.
  """
  fp = open( variable, 'r+b' );
  fp.seek( MARSHALLED_PYTHON_OFFSET );
  value = marshal.load( fp );

  value += 1;

  fp.seek( MARSHALLED_PYTHON_OFFSET );
  marshal.dump( value, fp );

  fp.close();

  return value;

def mkdir( path ):
  os.mkdir( path );

################################################################################
# dummy classes to mirror those in pstorage
class Object:
  def __init__( self, key ):
    self.key = key;

  def __repr__( self ):
    return 'Object(self,' + repr(self.key) +')';


class Dict:
  def __init__( self, key ):
    self.key = key;

  def __repr__( self ):
    return 'Dict(self,' + repr(self.key) +')';

class List:
  def __init__( self, key ):
    self.key = key;

  def __repr__( self ):
    return 'List(self,' + repr(self.key) +')';

class Method:
  def __init__( self, key ):
    self.key = key;

  def __repr__( self ):
    return 'Method(self,' + repr(self.key) +')';

class File:
  def __init__( self, content, content_type):
    self.content_type = content_type;
    self.content = content;

  def __repr__( self ):
    return 'File( ' + repr(self.content) + ', ' + repr(self.content_type) + ' )';

COMPLEX_TYPES = [ Object, Dict, List, Method, File ];
 
################################################################################

def validate_session( sessIP, sessID, hashID ):
  """
  This method validates and generates session information.

  sessIP is the ip address associated with the session - it is used to help
  obstruct session hijacking

  sessID is the purported ID (it must be validated)

  hashID - if hashID matches that used by the server for the given session,
  then the sessID is assumed to be valid.

  It returns a triple consisting of:
    sessionID - associated with this session
    username  - associated with this session
  """


  # peform a series of checks to determine if the session is valid
  # if anything goes wrong, fall through the bottom and generate a new
  # session

  # check if a session ID is supplied and the hashID is correct
  if sessID != None:
    if hashID != None:
      # both are supplied
      # figure out what the correct hash should be
      correct_hash = crypt( sessIP, sessID, salt=hashID, older=0 );
      older_hash = crypt( sessIP, sessID, salt=hashID, older=1 );

      if hashID==correct_hash or hashID==older_hash:
        sessID_path = os.path.join( storserv_config.SESSIONS_RPATH, 
                                    encode_index( sessID ) );


        return sessID, do_getattribute( sessID_path, 'username' );

  # if we get here, then the hash ID is invalid and the session should be
  # aborted and replaced by a new session

  # generate a new session ID and hash, set username to none

  # 1. get a key for the new session object use it as the session ID
  if sessID != None:
    sys.stderr.write( "SECURITY VIOLATION:  Invalid hash ID for session %s\n" %\
                      (sessID,) );


  #sessID = increment( storserv_config.sessID );


  # 2. attach that key to the session dictionary indexed by the key number

  # determine the key associated with the session object that stores 
  # all sessions

  # note: since this object is created based on a brand new object_key, 
  # and inserted into the session dictionary with an index equal to that
  # new object key there is no need to increment version numbers for 
  # previous dictionary entry values with the same index

  # now attach the new session to the session object
  #do_setitem_dict( sessID=sessID, 
  #                 obj_key=storserv_config.SESSIONS_RPATH, 
  #                 item_name=encode_index(sessID), 
  #                 item_value=None,
  #                 item_type=TYPES.Object );

  do_append_list( os.path.join( storserv_config.DATA_PATH, storserv_config.SESSIONS_RPATH ), Object(None) );

  sessID = do_len_list( storserv_config.SESSIONS_RPATH ) -1;

  sys.stderr.write( "SECURITY EVENT:      New hash ID: %s\n" % (sessID,) );


  sess_path = os.path.join( storserv_config.SESSIONS_RPATH, 
                            encode_index(sessID) );


  # 3. fill in information within the session object
  do_setattr( obj_key=sess_path, 
              attr_name='sessID', 
              attr_value=sessID );
  do_setattr( obj_key=sess_path, 
              attr_name='sessIP', 
              attr_value=sessIP );
  do_setattr( obj_key=sess_path, 
              attr_name='username', 
              attr_value='nobody' );
                      
  # 4. return the relevant information
  # (a fresh sessID, a matching hashID, and the username=nobody
  return sessID, 'nobody';
 
################################################################################

def recv( conn ):
  """
  This function receives data over the connection.  The data is read
  in MAX_MESSAGE_SIZE blocks of characters.  If the last character received
  is not the EOT character, then additional blocks are read and appended.
  """

  message = '';

  while True:
    message += conn.recv( storserv_config.MAX_MESSAGE_SIZE ).decode('UTF-8'); 
                       # receive data
    if message[-1]==storserv_config.EOT:
      break;

  return message[:-1];

################################################################################

def make_socket( pid ):
  """
  Establishes a socket connection.
  """
  if os.path.exists( storserv_config.SOCKET_PATH ):
    # a socket exists!  is the server already running?
    if os.path.exists( storserv_config.PID_FILE ):
      fp = open( storserv_config.PID_FILE );
      old_pid = int( fp.read() );
      fp.close();
      if os.path.exists( "/proc/%d\n" % old_pid ):
        # code is still running
        sys.stderr.write( "%s: Error, program is already running (pid=%d)" % \
                          (sys.argv[0],old_pid,) );
      else:
        os.unlink( storserv_config.PID_FILE );
        os.unlink( storserv_config.SOCKET_PATH );
    else:
      # socket exists, but not PID_FILE
      os.unlink( storserv_config.SOCKET_PATH );
  

  # initialize socket / run continuous loop  
  my_socket = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM );
  my_socket.bind( storserv_config.SOCKET_PATH );
  os.chmod( storserv_config.SOCKET_PATH, 0o766 );
  my_socket.listen(5);

  fp = open( storserv_config.PID_FILE, 'w' );
  fp.write( '%s' % (pid,) );
  fp.close();

  return my_socket;

################################################################################

def run_server():
  """
  This function operates the storserv server in a continuous loop.

  It establishes a socket.
  It listens on that socket accepting connections.
  Then, it runs in a continual loop receiving and processing messages.

  When messages are received:
    the session is validated or a new session is assigned
  """

  if not os.path.exists( storserv_config.DATA_PATH ):
    sys.stderr.write( 'Error:  DATA_PATH "%s" does not exists\n' % storserv_config.DATA_PATH );
    sys.exit(-1);

  pid = os.getpid();
  my_socket = make_socket(pid);

  # initalize database
  sys.stdout.write( 'Server ready;\n' );
  sys.stdout.write( '  pid: %s,\n' % (pid,) );
  sys.stdout.write( '  listening on socket: ' + \
                    storserv_config.SOCKET_PATH + '\n' );

  while True:
    try:
      conn = my_socket.accept()[0];

      result = recv( conn );

      # uncommenting the following line can compromise passwords as
      # the plain text may be written to a log file

      # sys.stdout.write( "\nReceived message: %s\n" % (result,) );

      # result should be a string containing an expression that evaluates to
      #     a 7-tuple as follows:
      # 0 - transmission type (currently must be "a" - ascii)
      # 1 - action (function to be executed, prefaced by "do_")
      # 2 - sessIP (IP address associated with the storage session making
      #     the request)
      # 3 - sessID (session ID associated with the storage session making
      #     the request)
      # 4 - hashIP (hash IP associated with the storage session making
      #     the request)
      # 5 - list of ordered arguements to be supplied to the function
      # 6 - dictionary of keyword arguments to be supplied to the function
      
      transmission, action, sessIP, sessID, hashID, args, vargs = \
            eval( result );

      # determine the actual session ID and hash ID and username based on
      # the requested values
      # actual and requested values will match if the supplied hashID checks
      # out

      validated_sessID, username = validate_session( sessIP, sessID, hashID );

      if transmission == 'a':   # ascii transmission

        # make sure the user has permissions
        if check_perm( validated_sessID, 
                       args[0], 
                       action, args[1:], username ) :
          function = eval( 'do_'+action );

          if action == 'get_session_info':
            args = (validated_sessID,);

          conn.send( bytes( repr( function( *args ) ) + \
                              storserv_config.EOT, \
                            'UTF-8' \
                          ) \
                   ); 

        else: # permission denied
          sys.stderr.write( 'SECUIRTY VIOLATION:  Permission denied: %s %s %s %s\n' % (username,action,args,vargs) );

          result = "self.raise_SCAccessException('%s','%s','%s')" % (args[0],action,username);
          conn.send( bytes( result + storserv_config.EOT, 'UTF-8' ) );

      else: # unsupported transmission format
        conn.send( 'self.raise_StorservException(%s%s)' % (
                     repr( 'StorservSyntaxError' ),
                     repr( 'Bad transmission '+transmission ) ) + \
                     storserv_config.EOT );
        sys.stderr.write( "Bad transmission: '%s'\n" % (transmission,) );

    except Exception as e:	# handle all possible exceptions, 
                                # but keep the server running

      sys.stderr.write( "Exception: %s\n" % (repr(e),) );
      #write_exception();

      try:
        conn.send( bytes( 'self.raise_StorservException(%s,%s)' % ( \
                            e.__class__.__name__, repr(pptraceback()), ) + \
                            storserv_config.EOT , \
                          'UTF-8' \
                        ) \
                 );
      except socket.error as e:
        pass;	# never give up
   
     # close the connection to the socket 
    conn.close();

  # while True

################################################################################

def permitted( allowed_roles, user_roles ):
  """
  Return true if there is an overlapping value between allowed_roles and
  user_roles (i.e. if the intersection between the allowed_roles and user_roles
  sets is non-null).
  """

  for role in user_roles:
    if role in allowed_roles:
      return True;
  return False; 

################################################################################

def check_perm( sessID, target, action, arguments, username ):
  """
  Determine whether the given username (string) has permission to perform 
  the given action (string) on the given target (int) with the given 
  arguments (list).

  Returns True or False.
  """

  # the root user has permission for everything
  if username=='root':
    return True;

  # determine the groups associated with the username
  roles = do_getroles( sessID, 0, username );

  if 'root' in roles:
    return True;

  # now work up from the target until we find an object that contains
  # a permissions attribute

  while (True):
    # try to get the permissions attribute from the target

    permission_list_key = os.path.join( target, 
                                        storserv_config.PERMISSIONS, action );

    permission_list_path = os.path.join( storserv_config.DATA_PATH, 
                                         permission_list_key );

    if os.path.exists( permission_list_path ):

      # if we get here, then we have found a permission object
      permission_list = do_getitem_list( permission_list_key, 
                                         slice(None) );


      return permitted( permission_list, roles );

    # else:
    # no permission found, check container
    if target=='':
      # if we get to the very top of the objects (storage) tree deny permission
      return False;

    target = do_getcontainer( sessID, target );

################################################################################

class ClientCommand:
  """
  This class provides a repr wrapper that permits the transmission of a
  command string through the repr function without being enclosed in an extra
  set of quotation marks.

  This allows client-side commands to be transmitted from do_ functions below
  and executed on the client-side.  Despite being subjected to a "repr" 
  function (which would normally super-enquote the string causing its evaluation
  as a string, rather than a command).

  The bottom line is that if you want to send a client-side command from
  within one of the do_ functions below, you can simply:
     return ClientCommand( "thecommand" );
  """

  def __init__( self, command ):
    self.command = command;

  def __repr__( self ):
    return self.command;

################################################################################

def decode( line ):
  """
  Decode the value stored in a line of data from the containment table.

  Note that a line is capable of sorting different object types in each of
  its data columns, but only one column will contain a value.  This function
  identifies the data type and then returns the appropriate column and casts
  the result to the appopriate python type.

  It returns the value None if the value of line is None.

  If the retreived line contains a pstorage object, then the value returned
  is a ClientCommand to construct the object (which can be executed 
  client-side).
  """

  if line==None:
    return None;

  object_type = line[4];

  if object_type == 'NoneType':
    return None;

  if object_type == 'Boolean':
    return bool(line[6]);

  elif object_type == 'Integer':
    return int(line[7]);

  elif object_type == 'LongInteger':
    return int(line[8]);

  elif object_type == 'Float':
    return float(line[9]);

  elif object_type == 'String':
    return str(line[10]);

  else:
    object_key = line[5];
    result = ClientCommand( "self.%s(%d)" % (object_type,object_key) );
    return result; 

################################################################################

################################################################################

################################################################################

################################################################################


################################################################################
################################################################################
################################################################################
################################################################################
# Storserv commands
################################################################################
################################################################################
################################################################################

def do_command( *argumentlist ):
  """
  The following functions which all start with "do_" are available to
  external programs via the socket.
  E.g. "do_login" can be accessed via the socket as "login".
  The remaining arguments are command specific and detailed in the sections
  below.

  Note that the first arugment in the argumentlist, must be an integer 
  indicating an object upon which the command is to be applied.

  The functions below are called in repsonse to a request from a client to
  this server.  Upon calling the function, the result is converted into a
  python expression by means of the "repr" built-in function and that
  expression is then transmitted to the client.  It is assumed that the
  client then uses the "eval" built-in function to evaluate the expression
  and use the result.

  client_result = eval( repr( do_command( argumentlist ) ) );
  """
  # this is a dummy command provided only as a documentation stub
  pass;

################################################################################
# get - commands                                                               #
################################################################################

################################################################################
def do_getattribute( obj_key, attr_name ):

  """
  Returns a ClientCommand object or a string that can be evaluated to
  create a python primitive type that represents the object that is 
  referenced by attr_name within the object given by obj_key.

  If the attribute does not exist in the given object, this will 
  raise an AttributeError.
  """

  try:
    value = path2value( os.path.join( obj_key, attr_name ) );
  except IOError as e:
    raise AttributeError("object %s has no attribute %s (%s)" % \
        ( repr(obj_key), repr(attr_name), str(e) ));

  return value;

################################################################################

################################################################################

################################################################################

def do_getcontainer( sessID, key ):
  """
  Return the key of object that contains the object identified by "key".

  Returns an string (or none if there is no container).
  """

  return os.path.dirname( key );
  
################################################################################

def do_getcontents( obj_key ):
  """
  Returns a list of items contained in the given object.
  """

  full_path = os.path.join( storserv_config.DATA_PATH, obj_key, '*' );

  return [ content_name for content_name in glob.glob( full_path ) if os.path.basename(content_name) != '__len__' ];


################################################################################

def do_getitem_dict( obj_key, item_index ):
  """
  Return the object that is referenced by item_index within the dict 
  given by obj_key.

  Raises a client side key error if the item_index does not exist in the
  obj_key.
  """

  relative_path = os.path.join( obj_key, item_index );

  try:
    return path2value( relative_path );
  except IOError as e:
    raise KeyError(repr(item_index));

################################################################################

def do_islink( obj_key ):
  """
  """

  full_path = os.path.join( storserv_config.DATA_PATH, obj_key );

  return os.path.islink( full_path );


################################################################################

def do_items( obj_key ):
  """
  """

  full_path = os.path.join( storserv_config.DATA_PATH, obj_key, '*' );

  return [ (os.path.basename(content_name), path2value(content_name)) \
                             for content_name in glob.glob( full_path ) ];


################################################################################

################################################################################

def encode_index( index ):
  if index==0:
    return '0';
  index2 = math.floor( math.log10( index ) )+1;
  index3 = math.floor( math.log10( index2 ) )+1;
  return '%d_%d_%d' % (index3,index2,index);

################################################################################

def decode_index( index ):
  if index=='0':
    return 0;
  return int( index.split('_')[2] );

################################################################################

def do_getitem_list( obj_key, item_index ):
  """
  Return the object(s) that is referenced by item index within the list given
  by obj_key.

  This suports both regular indices [3], and slices [3:7:1].

  In the former case, the decoded value at the given index is returned.
  In the latter, a list of decoded values are returned.

  If an invalid index is used in a non-slice, a client-side index error is 
  raised.
  """

  # single item request
  if type(item_index)==type(0):

    index_path = encode_index( item_index );
    path = os.path.join( obj_key, index_path );

    try:
      return path2value( path );
    except IOError:
      raise IndexError("List index out of range");

  # slice request
  elif type(item_index)==slice:

    files = [x for x in os.listdir( os.path.join( storserv_config.DATA_PATH, 
                                              obj_key ) ) if x[0] in '0123456789'];


    # determine start
    if item_index.start:
      start_pos = item_index.start;     # need to remember this as modulus of
                                        # the step size
    else:
      start_pos = 0; # need to remember this as a modulus of the step size

    if item_index.stop:
      stop_pos = item_index.stop;
    else:
      stop_pos = len(files);

    if item_index.step:
      step = item_index.step;
    else:
      step = 1;

    files = [ decode_index(file1) for file1 in files ];
    list_values = [ path2value( os.path.join( obj_key, encode_index(item) ) ) \
                  for item in sorted( files ) \
                    if item >= start_pos and \
                       item < stop_pos and \
                       item % step == start_pos % step ];

    return list_values;


################################################################################

attribute_regex = re.compile( '(.*)\.([A-Za-z_][A-Za-z_0-9]*)$' );
item_regex      = re.compile( '(.*)\[([^\[\]]*)\]$' );
top_level_regex = re.compile( '([A-Za-z_][A-Za-z_0-9]*)' );

#def do_getkey( sessID, base, path ):
#  """
#  Returns the integer key of the object given by path.  Which is assumed
#  to be relative to the key given by base.  If base==0, then the path
#  is resolved relative to the root.
#
#  This is basically the inverse of do_getcanonicalname (above).
#  Path can contain attributes (of objects), items (of dictionaries) and list 
#  elements (of lists).  Indices of dictionaries must be strings that do
#  not contain square brackets.
#
#  Only object keys can be returned (i.e. not singleton variables: strings, 
#  ints, etc. since they do not have keys).
#
#  This works by picking off the last item in the path, and recursively
#  calling on the preceeding part.
#
#  If the name does not map to any key, this raises an exception (server-side).
#
#  ToDo:
#  The item regex should be fixed to allow square brackets inside quoted
#  indices.
#  E.g. dictionary2[ 'key[x]' ]
#  which is valid python syntax by would be parsed out incorrectly here.
#  """
#
#  attribute = attribute_regex.match( path );
#  if attribute:
#    # look up an attribute
#    result = do_getattribute_key( sessID, 
#                            do_getkey( sessID, base, attribute.group(1) ), 
#                            attribute.group(2) );
#    return result;
#
#  item = item_regex.match( path );
#  if item:
#    key = eval( item.group(2) );
#
#    if type(key)==type(''):
#      # lookup an item in a dictionary
#      result = do_getitem_dict_key( sessID, 
#                              do_getkey( sessID, base, item.group(1) ), 
#                              key );
#
#      return result;
#
#    elif type(item)==type(0):
#      # lookup item in a list
#      result = do_getitem_list_key( sessID, 
#                              do_getkey( sessID, base, attribute.group(1) ), 
#                              attribute.group(2) );
#      return result;
#
#  top_level = top_level_regex.match( path );
#  if top_level:
#    result = do_getattribute_key( sessID, base, path );
##    return result;
#
#  raise Exception, "Bad path:  " + path;

################################################################################

def do_getroles( sessID, top, username ):
  """
  Return a list of roles associated with the given username.
  Username is a string.
  The value of top is not used.
  The return value is a list of strings or none if not roles are found.
  """

  roles_path = os.path.join( storserv_config.USERS_RPATH, username, 
                             storserv_config.ROLES_OBJECT );

  full_roles_path = os.path.join( storserv_config.DATA_PATH,
                                  roles_path, '*' )

  roles_list_names = sorted( glob.glob( full_roles_path ) );

  roles_list = [ path2value(item) for item in  roles_list_names ];
  roles_list.append( 'guest' );

  return roles_list;


################################################################################
# del commands                                                                 #
################################################################################
# These commands handle the deletion of containment relationshsips.            #
#                                                                              #
# When a containment relationship is thus deleted, its contained object        ## becomes inaccessible, as do any further objects contained within the         #
# contained object recursively.                                                #
# This could result in an object which still exists (in current_containment)   #
# that has no container.                                                       #
# This would be a violation of the principle that every object except the root #
# is contained within exactly one object.                                      #
#                                                                              #
# In order to resolve this constraint violation, we consider 2 options:        #
# 1) the deletion of objects containing other objects should be prohibited     #
# 2) the deletion of objects containing other objects initiates the automatic  #
#    deletion of the closure of the containment relation (all contained        #
#    must be recursively deleted).                                             #
#                                                                              #
# Option 1) is not very pythonic (in regular python del operations do not      #
#   fail).                                                                     #
# Option 2) is potentially very destructive and computationally intensive if   #
#   a large heirarchy is to be destroyed (like rm -rf).                        #
#                                                                              #
# We chose Option 2).                                                          #
# Though, Option 1) could still be implemented in pstorage or higher level     #
# calling functions/methods.                                                   #
#                                                                              #
# A second issue is the deletion (either direct, or recursively) of objects    #
# that are linked to.                                                          #
# This would result in links that link to objects that have been deleted.      #
# In this case the object in the database will have a version number >0,       #
# or possibly be deleted from the database entirely, due to a purge.           #
#                                                                              #
# We consider 2 options:                                                       #
# 1) prevent the deletion of objects that are linked-to                        #
# 2) allow broken links to exist,                                              #
# 3) while deleting objects, also delete links to them,                        #
#                                                                              #
# Once again, option 1) is not very pythonic.                                  #
# Option 2) can cause problems when the links are followed.  There would need  #
#   to be a check at the time of dereferncing to see if the object still       #
# Option 3) is potentially destructive and increases the work associated with  #
#   a delete operation.                                                        #
#                                                                              #
# We chose option 3).
# Though, Option 1) could still be implemented in pstorage or higher level     #
# calling functions/methods.                                                   #
################################################################################

################################################################################

  
def do_delattr( obj_key, attr_name ):

  """
  Delete the attribute named attr_name from the object identified by obj_key.
  """

  full_path = os.path.join( storserv_config.DATA_PATH, obj_key, attr_name );

  if os.path.exists( full_path ):
    if os.path.isdir( full_path ) and not os.path.islink( full_path ):
      shutil.rmtree( full_path );
    else:
      os.unlink( full_path );
  else:
    raise AttributeError("object %s has no attribute '%s'" % \
      ( do_getcanonicalname( sessID, obj_key ), attr_name, ));


################################################################################

def do_delitem_list( obj_key, item_index ):
  """
  Delete the item specified by key from the object specified by item_index.

  This one is complicated because all the higher indexed items must be moved
  down!
  """
  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );
  len_val = path2value( len_path );

  # adjust for negative indices
  if item_index < 0:
    item_index = len_val-item_index; 

  if item_index==len_val-1:
    # deleting last item
    item_new_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                                  encode_index( item_index ) );
    if os.path.isdir( item_new_path ) and not os.path.islink( item_new_path ):
      shutil.rmtree( item_new_path );
    else:
      os.unlink( item_new_path );
    
  for index in range( item_index, len_val-1 ):
    item_new_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                                  encode_index( index ) );
    item_old_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                                  encode_index( index+1 ) );

    os.rename( item_old_path, item_new_path );

  
  value2path( len_val-1, len_path );

################################################################################

def do_delitem_dict( obj_key, item_name ):
  """
  Delete the item spcified by key from the object specified by obj_key.
  We assume that this function is called on Dictionary objects, while the
  function do_delitem_list is used for List objects.
  """

  item_path = os.path.join( storserv_config.DATA_PATH, obj_key, item_name );

  if os.path.isdir( item_path ) and not os.path.islink( item_path ):
    shutil.rmtree( item_path );
  else:
    os.unlink( item_path );

################################################################################
# set - commands                                                               #
################################################################################


def do_setattr( obj_key, attr_name, attr_value ):

  """
  Set the value of the attribute attr_name in the object given by obj_key
  to the value given by attr_value with the type given by attr_type.

  The way in which it is set depends on attr_type:
    if attr_type is an Object, content_key is set,
    if attr_type is a String, attr_string is set, 
    etc.

  """

  value2path( attr_value, os.path.join( obj_key, attr_name ) );

  return attr_value;

################################################################################

################################################################################

def fix_list__len__( obj_key ):
  list_path = os.path.join( storserv_config.DATA_PATH, obj_key, '[0-9]*' );
 
  len_val = len( glob.glob( list_path ) );
  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );

  value2path( len_val+1, len_path );

################################################################################

def do_append_list( obj_key, item_value ):
  """
  Append an item to the end of the list.
  """

  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );
  try:
    len_val = path2value( len_path );
  except IOError as e:
    len_val = 0;
  
  item_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                            encode_index( len_val ) );

  try:
    value2path( item_value, item_path );
  except OSError as e:	# this code runs if __len__ value is too small
    print(">>>", e);
    fix_list__len__( obj_key );
    do_append_list( obj_key, item_value );

  value2path( len_val+1, len_path );


################################################################################

def do_extend_list( list1, list2 ):
  # list1 is a pstorage list object, list2 is a python list
  len_path = os.path.join( storserv_config.DATA_PATH, list1, '__len__' );
  len_val = path2value( len_path );

  for item_value in list2:
    item_path = os.path.join( storserv_config.DATA_PATH, list1,
                              encode_index( len_val ) );

    value2path( item_value, item_path );
    len_val += 1;

  value2path( len_val, len_path );

################################################################################

def do_setitem_list( obj_key, item_index, item_value ):

  """
  Set the value of the item item_index in the object given by obj_key
  to the value given by item_value with the type given by item_type.

  Note this is a setitem, not an insert item.
  It should not be accomplished by a do_delitem_list (because that moves
  too many elements around).

  The way in which it is set depends on attr_type:
    if attr_type is an Object, content_key is set,
    if attr_type is a String, attr_string is set, 
    etc.
  """
  item_path = os.path.join( storserv_config.DATA_PATH, obj_key,
                            encode_index( item_index ) );

  if not os.path.exists( item_path ):
    raise IndexError("list assignment index out of range");

  value2path( item_value, item_path );

################################################################################

def do_setitem_dict( obj_key, item_name, item_value ):
  """
  Set the value of the item item_name in the object given by obj_key.

  The way in which it is set depends on item_type:
    if item_type is an Object, content_key is set,
    if item_type is a String, content_string is set, 
    etc.
  """
 
  item_path = os.path.join( storserv_config.DATA_PATH, obj_key, key2path(item_name) );
  
  value2path( item_value, item_path );

################################################################################

def do_len_dict( obj_key ):
  # might cause a problem if some keys start with a period
  item_path = os.path.join( storserv_config.DATA_PATH, obj_key, '*' );
  return len( glob.glob( item_path ) );

################################################################################
# Object Constructor function
################################################################################

################################################################################
# has functions
################################################################################

# special List functions
################################################################################

def do_len_list( path ):
  # see also do_length
  return path2value(  os.path.join( path, '__len__' ) );

################################################################################

def do_insert( obj_key, item_index, item_value ):
  """
  Insert the given item_value of type item_type into the list identified by
  obj_key at the position given by item_index.  In the process, increment
  the indices of all the items that are greater than or equal to item_index
  by 1.
  """

  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );
  len_val = path2value( len_path );
 
  for index in range( len_val-1, item_index-1, -1 ):
    # count down, so you don't thrash the old values before you've copied them
    item_old_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                                  encode_index( index ) );

    item_new_path = os.path.join( storserv_config.DATA_PATH, obj_key, 
                                  encode_index( index+1 ) );

    os.rename( item_old_path, item_new_path );

  item_path = os.path.join( storserv_config.DATA_PATH, obj_key,
                                  encode_index( item_index ) );

  value2path( item_value, item_path );
  
################################################################################

def do_reverse( obj_key ):
  """
  reverse the items of the list in place
  """

  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );
  len_val = path2value( len_path );

  for src,dest in zip( list(range( 0, (len_val+1)//2)), 
                       list(range( len_val-1, (len_val-1)//2, -1)) ):
    src_path = os.path.join( storserv_config.DATA_PATH, obj_key,
                                  encode_index( src ) );
    dest_path = os.path.join( storserv_config.DATA_PATH, obj_key,
                                  encode_index( dest ) );

    src_val = path2value( src_path );
    dest_val = path2value( dest_path );

    value2path( src_val, dest_path );
    value2path( dest_val, src_path );

  
################################################################################

#def do_length( obj_key ):
#  """
#  Return the length of the list given by obj_key.
#  """
#  len_path = os.path.join( storserv_config.DATA_PATH, obj_key, '__len__' );
#  return path2value( len_path );



################################################################################
# user access
################################################################################

def do_check_user( sessID, top, username, password ):
  """
  Check if the new_user's password matches the password provided.

  The value of top is not used in this function (only for permissions check).

  Return True if the password is OK, False otherwise.

  This does not actually log-in the user (use do_login for that).

  ***Should this be slowed down to stimey a brute force password attack?***
  """
  
  # determine the password mechanism used:  
  #   htpassword file or htpasswords in the database

  time.sleep(1.0);

  try:
    # retrive the user's password attribute from the database
    try:
      correct_password = path2value( os.path.join( storserv_config.USERS_RPATH,
                                                   username, storserv_config.PASSWORD ) ); 
    except IOError as e: # No password entry for user
      return False;


    # construct HTPasswdEntry object which
    correct_password = htpasswd.HTPasswdEntry( username, correct_password );

    # compare the user's password attribute to the one provided
    if correct_password==password:
      return True;
    else:
      return False; # htpasswords are in the database but suppied password is 
                    # wrong

  except KeyError as e:   
               # if that didn't work (i.e. if the user didn't have a 
               # password attribute) ... try something else:
    pass;

#  try:
#    # find the server in the database
#    server = do_getkey( sessID, 0, storserv_config.SERVER_PATH );
#
#    # retrieve the htpasswd attribute to get filename
#    filename = do_getattribute( sessID, server, "htpasswd" );
#
#    # create password file object
#    passwd = htpasswd.HTPasswdFile( filename );
#
#    if passwd[username]==password:
#      return True;
#    else:
#      return False;
#
#  except AttributeError, e:
#    pass;

  return False;	# if anything extraordinay happended return False

################################################################################

def do_login( top, validatedSessID, new_user, password ):
  """
  Verify the new_user's password.  If the password matches the stored password,
  set the attribute "username" to equal "new_user" in the session and return 
  the value.

  If the password is incorrect, leave the "username" attribute in the session
  anlone and return its value.

  NOTE:  any password is considered valid for the user 'nobody".
  """

  # if the request is to switch to user nobody, we always allow it
  # if the request provides the valid password for the given username, allow it

  session_path = os.path.join( storserv_config.SESSIONS_RPATH, 
                               encode_index( validatedSessID ) );

  old_user = do_getattribute( session_path, 'username' );
 
  if new_user=='nobody' or do_check_user( validatedSessID, 0, 
                                          new_user, password ):

    sys.stderr.write( "SECURITY EVENT:      Successful log-in attempt by %s to %s\n" % ( \
                     old_user, new_user,) );

    # set the user attribute of the session to equal the user ID
    do_setattr( session_path, 'username', new_user );
    return new_user;

  else:
    sys.stderr.write( 
            "SECURITY VIOLATION:  Failed log-in attempt by %s to %s\n" % \
                     (old_user,new_user,) );

    return ClientCommand( "self.raise_SCLoginException('%s','%s')" % \
                          (old_user,new_user,) );



################################################################################

def do_create_user( new_user, password ):
  """
  Create a new user with the default roles given in the DEFAULT_ROLES_LIST List
  specified in storserv_config.py if the user doesn't already exist.
  """
  # TODO: have a list of protected names

  default_roles_path = storserv_config.DEFAULT_ROLES_RPATH

  user_path     = os.path.join( storserv_config.USERS_RPATH, new_user );
  password_path = os.path.join( user_path, storserv_config.PASSWORD );
  roles_path    = os.path.join( user_path, storserv_config.ROLES_OBJECT );

  if os.path.exists( os.path.join( storserv_config.DATA_PATH, user_path ) ):
    raise Exception("User already created.");
  else:
    print( "Path: " + user_path + " does not exist" );

  value2path( Object(None), user_path );

  magic, salt, code = htpasswd.md5crypt(password);
  password_bytes = magic + salt + b'$' + code;

  value2path( password_bytes, password_path );
  value2path( List(None), roles_path  );

  do_append_list( roles_path, new_user );

  for i in range( do_len_list(default_roles_path) ):
    do_append_list( roles_path, do_getitem_list( default_roles_path, i ) );

################################################################################

def do_get_session_info( validated_sessID ):
  """
  Return relevant session information.
  """

  validated_sessID_path = os.path.join( storserv_config.SESSIONS_RPATH,
                                        encode_index(validated_sessID) );

  sessIP = path2value( os.path.join( validated_sessID_path, 'sessIP' ) );
  username = path2value( os.path.join( validated_sessID_path, 'username' ) );

  return validated_sessID, crypt( sessIP, validated_sessID ), username;
  
################################################################################
################################################################################
################################################################################

def current_user(): 
  return pwd.getpwuid(os.getuid())[0];

################################################################################

def do_getattributes( obj_key ):
  """
  Return the attribute_name of each of the rows of the table for which the 
  container key is obj_key
  i.e.. all the objects contained in the object given by "obj_key"
  The attribute names are sorted alphabetically.

  The return value is a list of strings.
  """

  path = os.path.join( storserv_config.DATA_PATH, obj_key );

  attr_list = os.listdir( path );
  filter_list = [];

  for i in range( len( attr_list ) ):
    if attr_list[i][0] != '.':
      filter_list.append( attr_list[i]);

  return filter_list;

################################################################################

if __name__ == '__main__':
  # if this code is being run as an executable

  server_key = make_salt(64);	# use a 64*6 bit random number to encode
				# session hashes so that they cannot be
				# hacked
  
  # reconstruct command line
  command_line = 'python ' + reduce( lambda x,y: x+' '+y, sys.argv );

  if current_user()!='root':
    sys.stderr.write( 'This program is running as user %s\n' % \
                       ( current_user(), ) );
    sys.stderr.write( 'Error:  This program must started as root!\n' );
    sys.stderr.write( 'Please restart this program while running as user '
                      'root!\n' );
    sys.exit(-1);


  try:
    os.mkdir( storserv_config.RUN_PATH );
  except OSError as e:
    # directory already exists
    # anything else could cause this error for user root?
    pass;

  # fix ownership of DATA_PATH
  os.system( 'chown -R %s %s' % ( storserv_config.USERNAME, \
                                   storserv_config.DATA_PATH ) );

  try:
    pstorage_uid = pwd.getpwnam( storserv_config.USERNAME ).pw_uid;
    pstorage_gid = pwd.getpwnam( storserv_config.USERNAME ).pw_gid;
  except KeyError as e:
    sys.stderr.write( 'Error:  User %s does not exist.\n' % \
                      storserv_config.USERNAME );
    sys.stderr.write( 'Please add a user named, %s, to your operating '
                      'system.\n'% storserv_config.USERNAME );
    sys.exit(-1);

  try:
    os.chown( storserv_config.RUN_PATH, pstorage_uid, pstorage_gid );
  except OSError as e:
    # don't think this can actually happen for root user
    pass;

  os.setuid( pwd.getpwnam(storserv_config.USERNAME).pw_uid );
  # should now definately be pstorage  

  sys.stdout.write( "pstorage server (storserv.py) v.6.0, (C) 2011\n" );
  sys.stdout.write( "  %s\n" % (SVN_INFO['HeadURL'],) );
  sys.stdout.write( "  SVN Revision: %s (%s, %s [%s])\n" % (
                       SVN_INFO['Revision'],
                       SVN_INFO['Date'][27:-1],
                       SVN_INFO['Date'][11:19],
                       SVN_INFO['Author'],) );
  #sys.stdout.write( "  %s\n" % (SVN_INFO['Id'],) );
  sys.stdout.flush();

  if storserv_config.PROFILE_FILE:
    sys.stdout.write( "  Profiling to: '%s'.\n" % (storserv_config.PROFILE_FILE,) );
    sys.stdout.flush();
    import cProfile;
    cProfile.run( 'run_server()', storserv_config.PROFILE_FILE );
  else:
    run_server();

################################################################################
'''
Lost functions!

Why is there no test for the functionality of these items?



def setany( obj_key, attr_name, item_name, item_index, attr_value, 
               attr_type ):

def delcontainer( sessID, obj_key ):
  """
  Delete the contents of a container given by obj_key.

  The contents MUST be empty before the container is deleted.

  There MUST be no links to the contents.

  If you do not know whether the object is empty and unlinked-to, then
  you should use the do_delall instead.

def delcontent( sessID, obj_key ):
  """
  Delete the given obj_key as the content of any containment relations.

  The contents MUST be empty before the container is deleted.

  There MUST be no links to the contents.

  If you do not know whether the object is empty and unlinked-to, then
  you should use another method instead.
  """

def delattribute( sessID, obj_key, attr_name ):
  """
  Delete an attribute of an object.

  The attribute must be empty before it is deleted.
  There MUST be no links to the attribute if it is an object.

  If you do not know whether the object is empty and unlinked-to, then
  you should use the do_delall instead.
  """

def do_getattributes( sessID, obj_key ):
  """
  Return the attribute_name of each of the rows of the table for which the 
  container key is obj_key
  i.e.. all the objects contained in the object given by "obj_key"
  The attribute names are sorted alphabetically.

  The return value is a list of strings.
  """
  return os.listdir( obj_key );

def do_getattrname( sessID, attr_key ):

  """
  Find the container object of the object given by attr_key and return
  the name of the attribute that references the attr_key (but do not return
  the container object).

  Returns a string (or None if the object is not found as an attribute of any
  container).
  """

def do_getitem_dict_key( sessID, obj_key, item_index ):
  """
  Return the key of the object that is referenced by item_index within 
  the dict given by obj_key.
  If the attribute does not exist in the given object, this will raise an
  AttributeError.

  If the attribute is not an object, this function returns None.
  """


def do_dellinksto( sessID, obj_key ):
  """
  Delete all links to the given obj_key.

  object.mylink -> (LinkObject).__referenced_object_key__ => obj_key
  """

def do_delall( sessID, obj_key ):
  """
  Recursively delete all attributes and items in the object given by obj_key.
  Delete all links to obj_key and finally delete obj_key itself.
  """

def do_new_object( sessID, top ):
  """
  Create a new Object and return the Object's __key__

  The value of top is not used in the function (only for permissions).
  """

def do_hasattr( sessID, obj_key, attr_name ):

  """
  Return True(False) if the object identified by obj_key has(does not have)
  an attributed named attr_name.
  """
  
################################################################################

################################################################################


################################################################################
                       
'''
