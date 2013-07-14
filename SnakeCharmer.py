#!/usr/bin/python3
# SnakeCharmer.py
# web server

"""
SnakeCharmer 6.0
Feb. 2011
Standalone SnakeCharmer Implementation (requires neither mod_python nor apache).
Based on python 3

Status:  In-development.

ToDo:
test ability to forward svn requests:
   http://code.activestate.com/recipes/483730-port-forwarding/

make http request to https server not generate an internal python error
and instead produce a "Bad Request" http response like Apache does.
-this is tough see below

References
http://code.activestate.com/recipes/442473-simple-http-server-supporting-ssl-secure-communica/

Notes
=====
Generating a PEM file:
openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes

Note: Common Name should be the web-site's name.


Country Name (2 letter code) [AU]:CA
State or Province Name (full name) [Some-State]:Ontario
Locality Name (eg, city) []:Guelph
Organization Name (eg, company) [Internet Widgits Pty Ltd]:kremer.ca
Organizational Unit Name (eg, section) []:
Common Name (eg, YOUR name) []:www.kremer.ca
Email Address []:stefan@kremer.ca
"""


################################################################################
# import some useful modules
################################################################################
# Standard python modules

import sys;
import SnakeCharmer_config;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);


import socket; 
from socketserver import BaseServer;
from socketserver import ThreadingMixIn;
from http.server import HTTPServer;
from http.server import BaseHTTPRequestHandler;
#from http.server import SimpleHTTPRequestHandler;
#from OpenSSL import SSL;

import http.client;
import ssl;

import os;
import re;
import time;
import http.cookies;
import urllib.request, urllib.parse, urllib.error;
import platform;
import traceback;

import cgi;

# custom python modules

import pstorage;
from functools import reduce;

################################################################################
# SVN Info
################################################################################

svn_regex = re.compile( r'^\$[^:]*: (.*) \$$' );

SVN_INFO = {
  'Date': """$Date: 2012-06-28 12:14:24 -0400 (Thu, 28 Jun 2012) $""",
  'Revision': """$Revision: 3485 $""",
  'Author': """$Author: stephen $""",
  'HeadURL': """$HeadURL: https://www.kremer.ca/svn/Repository/Projects/SnakeCharmer/6.0/SnakeCharmer.py $""",
  'Id': """$Id: SnakeCharmer.py 3485 2012-06-28 16:14:24Z stephen $""",
  };

for key in SVN_INFO:
  try:
    SVN_INFO[ key ] = svn_regex.match( SVN_INFO[ key ] ).group(1);
  except AttributeError as e:
    print(SVN_INFO[ key ]);
    raise;

__version__ = "6.0alpha (%s)" % (SVN_INFO['Revision']);

server_version = "SnakeCharmer/" + __version__;


# Note you must give the command:
#  svn propset svn:keywords "Date Revision Author HeadURL Id" SnakeCharmer.py
# for this to work.
################################################################################

# Useful constant

userdirregex = re.compile( r'/~([^/]*)(.*)' );
	# a regex to match the user directory

urisep = re.compile( r'\.|/' );
	# a regex to match URI separator characters: . | / 


################################################################################


def log( msg ):
  """
  Print stuff to the apache error log.

  If msg is a list, each element in the list is processed recursively.
  If msg is a string, it is split based on new-lines and each line
  is printed to the log.

  All other formats generate an exception.
  """

  if type(msg)==type([]):
    for line in msg:
      log( line );
    return;

  if type(msg)==type(""):
    for line in msg.split('\n'):
      sys.stderr.write( line + '\n' );
    sys.stderr.flush();
    return;

  raise Exception("Bad log message format:  %s" % (type(msg),));

################################################################################

def remove_dots( hostname ):
  """
  Replace dots in the hostname with underscores.
  """

  if hostname[0] in '0123456789':
    return '_' + hostname.replace( '.', '_' );
  else:
    return hostname.replace( '.', '_' );

################################################################################

def fix_char( char ):
  """
  This function translates a single character.  It is used to convert URLs into
  Python references.
  """
  if char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789':
    return char;
  else:
    return '__%02x__' % (ord(char),);


###############################################################################

def fix_path( path ):
  """
  This function translates all charcters.  It is used to convert URLs into
  Python references.
  """
  return ''.join( [ fix_char(char) for char in path ] );

###############################################################################

class text2html:
  """
  This class is a wrapper for the http response stream that converts strings
  that are written to it into html.  It is useful if you want to be able
  to print regular text in a response with content-type: text/html.

  Is this still being used anywhere???
  """

  def __init__( self, fp ):
    """
    Remember the file stram.
    """
    self.fp = fp;

  def write( self, text ):
    """
    Replace offensive characters.
    """
    text = text.replace( '<', '&lt;' );
    text = text.replace( '>', '&gt;' );
    text = text.replace( ' ', '&nbsp;' );
    text = text.replace( '\n', '<br/>\n' );
    self.fp.write( text );

###############################################################################

class HTTPError( Exception ):
  """
  This class is a new exception that can the raised when an HTTP error occurs.

  E.g. a 404 error.
  """

  def __init__(self,errno,target,msg,hostname,port):
    self.args = (errno,target,msg,hostname,port);
    self.errno = errno;
    self.title = http.client.responses[self.errno];
    self.msg = msg;
    self.target = target;
    self.server = server_version + ' (' + \
                  platform.dist()[0] + ") Server at " +\
                  hostname + " Port " + port;

###############################################################################


class SecureSnakeCharmerServer( ThreadingMixIn, HTTPServer):
  """
  This class represnets an HTTPS capable webserver.
  """
  def __init__(self, server_address, HandlerClass):

    BaseServer.__init__(self, server_address, HandlerClass);


    fpem = SnakeCharmer_config.fpem;

    http_socket = socket.socket( self.address_family, self.socket_type);

    print( fpem );
    self.socket = ssl.wrap_socket( 
      http_socket,
      server_side=True,
      certfile=fpem,
      cert_reqs=ssl.CERT_NONE,
      ssl_version=ssl.PROTOCOL_SSLv23,
      do_handshake_on_connect=False
    );

    self.server_bind();
    self.server_activate();


  def handle_error( self, request, client_address ):
    # Override default behaviour of error handler in ThreadingMixIn
    # the default handler prints and error message to stdout and stderr.
    # Instead, this re-raises the exception so that it can be caught and 
    # dealt with sensibly!

    print("handle_error!");
    exc_type, exc_value, exc_traceback = sys.exc_info();
    #if exc_type == SSL.Error and exc_value[0][0][2]=='http request':
    print(exc_type);
    print(exc_value);
    print(exc_traceback);
    print("OpenSLL error detected!");

      # We would like to send back a BadRequest to the web-client indicating
      # that they made an http request to this https server (like apache does).
      # But this response message must be sent via http (not https), but this 
      # server's __init__ function sets up an SSL server, so this seems
      # difficult to to.
      # It might be possible to make a mixed server than can serve both types
      # of requests, but this is left for later.

    # Fall back to original error handler.
    # Print: exc_type, exc_value, exc_traceback.
    BaseServer.handle_error( self, request, client_address );

###############################################################################

class SnakeCharmerServer( ThreadingMixIn, HTTPServer):
  """
  Regular SnakeCharmerServer with threading.

  It is just a mix of the TreadingMixIn and the HTTPServer.
  """

###############################################################################


class SnakeCharmerHandler(BaseHTTPRequestHandler):
  """
  This class handles the HTTP(S) requests.
  """
  def __init__( self, req, client, server ):
    BaseHTTPRequestHandler.__init__( self, req, client, server );
    self.protocol_version = 'HTTP/1.1'; # to allow persistent connections
    print( self.protocol_version );

  def get_cookie( self ):
    """
    Attempt to retreive and return a sessID and hashID from the cookie.

    'INVALID COOKIE' is printed to the error log if the cookie is improperly
    fomatted.

    NOTE:  No authentication is done here.
    """

    # look for session info in the cookie
    try:
      # look for cookies in the headers
      raw_cookie = self.headers['Cookie'];
      log( "Got Cookie: " + repr(raw_cookie) );

      try:
        # find cookie called SnakeCharmer
        c_str = str( http.cookies.SimpleCookie( raw_cookie )['SnakeCharmer'].value );

        # extract sessID, and hashID
        result = c_str.split(' ');
        if len(result)==2:
          return result;
        else:
          log('INVALID COOKIE '+repr(raw_cookie));
      except KeyError as e:
        log('INVALID COOKIE '+repr(raw_cookie));
      except ValueError as e:
        log('INVALID COOKIE '+repr(raw_cookie));
    except KeyError as e:
      log('NO COOKIE');

    log( "done get_cookie" );
    return "0", "";


  ##############################################################################

  def bake_cookie( self ):
    """
    Create cookie string, add it as an attribute to self (SnakeCharmerHandler).
    """
    c = http.cookies.SimpleCookie();
    c[ 'SnakeCharmer' ] = str(self.storage.__connection__.__sessID__) + " " + \
                          str(self.storage.__connection__.__hashID__);

    c[ 'SnakeCharmer' ]['path'] = "/";
    c[ 'SnakeCharmer' ]['expires'] = time.strftime( \
                                       "%a, %d-%b-%Y %H:%M:%S GMT", \
                                       time.gmtime( \
                                         time.time() + \
                                         SnakeCharmer_config.cookie_expiration \
                                       ) 
                                     );

    #c[ 'SnakeCharmer' ]['domain'] = self.hostname;
    self.cookie = c.output();

  ##############################################################################

  def send_head( self , ctype='text/plain'):
    """
    Send the standard HTML response header.
    200 OK (the request has succeeded).
    """
    self.send_response( http.client.OK )
    self.send_header( "Content-type", ctype )
    self.send_header( "Set-Cookie", self.cookie );
    self.end_headers()

  ##############################################################################

  def write( self, text ):
    """
    Writes the given text to the client.
    """
    if type( text ) == bytes:
      self.wfile.write( text );
    else:
      self.wfile.write( bytes(text,'UTF-8') );

  ##############################################################################

  def get_form( self ):
    """
    Retrive from data from a POST request or from a GET get request and
    store it in a dictionary called self.form.
    """

    if self.form_data == '':
      self.form = {};
    else:
      self.form = dict( [ item.split('=') \
                            for item in self.form_data.split('&') ] );
    if self.command=='POST':
      fieldstorage = cgi.FieldStorage( fp = self.rfile, \
                                       headers = self.headers, \
                                       environ = { \
                                         'REQUEST_METHOD': \
                                            'POST', \
                                         'CONTENT_TYPE': \
                                            self.headers['Content-Type'], \
                                       }
                                     );

      for key in list(fieldstorage.keys()):
        if fieldstorage[key].filename:
          self.form[key] = fieldstorage[key];
        else:
          self.form[key] = fieldstorage[key].value;


  ##############################################################################

  def getpsreq( self ):
    """
    Translate a URI into a path within pstorage.

    This method processes information in the self object and adds the following
    attributes:

    ps_site     - persistent storage path to site object
    ps_object   - path to page object relative to the site object
    ps_method   - name of the method object within the ps_object  
    """

    # first unescape the path to restore characters not allowed in URIs
    clean_path = urllib.parse.unquote_plus( self.path );

    # see if it matches the pattern for a user directory (starts with tilde)
    match = userdirregex.match( clean_path );
    if match:
      # set site attribute to user's PublicHTML directory
      uri_site_path = '/Server/Users/%s/PublicHTML' % (match.group(1));
      uri_object_path   = match.group(2); # get object with method
    else:
      # set site attribute to hostname directory
      uri_site_path = '/Server/WebSites/' + remove_dots( self.hostname );
      uri_object_path = clean_path;        # get object with method

    # now we have an absolute uri path, need to convert it to pstorage 
    # object by walking the path, and calling the objects' uri2py methods
    # at each node

    try:
      uri_site_path = [_f for _f in urisep.split( uri_site_path ) if _f];

      self.ps_site   = reduce( lambda x,y: x.uri2py(y), 
                               uri_site_path,
                               self.storage );

      uri_object_path = [_f for _f in urisep.split( uri_object_path ) \
                                      if _f];

      try:
        self.ps_object = reduce( lambda x,y: x.uri2py(y),
                               uri_object_path,
                               self.ps_site );
      except AttributeError as e:
        try:
          self.ps_object = reduce( lambda x,y: x.uri2py(y),
                                   uri_object_path[:-2]+[uri_object_path[-2]+\
                                     '.'+uri_object_path[-1]],
                                   self.ps_site );
        except AttributeError as e:
          raise HTTPError( http.client.NOT_FOUND, self.path, "Can't find ", \
                       self.hostname, self.hostport );
    except AttributeError as e:
      raise HTTPError( http.client.NOT_FOUND, self.path, "Can't find ", \
                       self.hostname, self.hostport );

    if isinstance( self.ps_object, pstorage.Method ):  
      # its a method, back off one to find container object
      self.ps_method = self.ps_object;
      self.ps_object = self.ps_method.__container__;
      if hasattr(self.ps_object, 'send_reply'):
        self.ps_send_reply=self.ps_object.send_reply;
      else:
        self.ps_send_reply=None;

    elif isinstance( self.ps_object, pstorage.Object ):
      # referenced object is Object
      self.ps_object = self.ps_object.index;
      self.ps_method = self.ps_object.html;
      if hasattr(self.ps_object, 'send_reply'):
        self.ps_send_reply=self.ps_object.send_reply;
      else:
        self.ps_send_reply=None;

    elif isinstance( self.ps_object, pstorage.Dict ):
      # referenced object is Dict
      self.ps_object = self.ps_object['index'];
      self.ps_method = self.ps_object.html;
      if hasattr(self.ps_object, 'send_reply'):
        self.ps_send_reply=self.ps_object.send_reply;
      else:
        self.ps_send_reply=None;

    elif isinstance( self.ps_object, pstorage.File ):
      # referenced object is File
      self.ps_method = self.ps_object.getcontent;
      self.ps_send_reply=None;

    else:
      # something else (primitive or List?)
      raise Exception( "Unsupported datatype found at "+self.path );

  ##############################################################################

  def send_reply( self , **args ):
    """
    Code to send a reply to the client.
    """

    # set some defaults
    self.response = http.client.OK;
    self.content_type = 'text/html';
    self.content = 'Content undefined!';

    # call the method to replace defaults with something more interesting
    self.ps_method( self, **args);

    #print("\n\n\n\n\nThis: ", self.content_type)

    # set the value of the response code to send
    self.send_response( self.response );

    # set the Content-type and Cookie info
    self.send_header( "Content-type", self.content_type );
    self.send_header( "Set-Cookie", self.cookie );
    self.end_headers();

    # actually send it
    self.write(self.content);

    # return the value of the response code sent via HTTP also to the calling
    # function
    return self.response;

  ##############################################################################

  def handle_any( self ):
    """
    Serve any kind of request:  GET, POST, etc..
    """

    log( "Connection from " + self.client_address[0] + " >" + \
         self.requestline );

    # set some useful attributes
    self.scheme = self.request_version.split('/')[0].lower();
    try:
      self.hostname, self.hostport = self.headers['host'].split(':');
    except ValueError as e:   # no port given
      self.hostname = self.headers['host'];
      self.hostport = None;
    try:
      self.path, self.form_data = self.path.split('?');
    except ValueError as e:   # no form data
      self.form_data = '';
    self.get_form();

    # retrieve, validate and update session info
    sessID, hashID = self.get_cookie();

    self.storage = pstorage.Storage( self.client_address[0], int(sessID), hashID );
    self.bake_cookie();

    try:
      self.getpsreq();
    except HTTPError as e:
      pstorage.log_exception();
      # generate an HTML error code response page
      ctype = 'text/html';
      self.send_response( e.args[0] );
      self.send_header( "Content-type", ctype );
      self.send_header( "Set-Cookie", self.cookie );
      self.end_headers();
      self.write( """
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>%(errno)d %(title)s</title>
</head><body>
<h1>%(title)s</h1>
<p>%(msg)s %(target)s
on this server.</p>
<hr>
<address>%(server)s</address>
</body></html>
""" % (e.__dict__) );
      return e.args[0];

    # send the header
    #self.send_head();

    log( 'sending reply' );

    if self.ps_send_reply:
      self.ps_send_reply( self, **(self.form) );
    else:
      self.send_reply();
      #self.send_reply( self, **(self.form) );


  ##############################################################################

  def handle_one_request(self):
    """Handle a single HTTP request.

    This is overridden so that all types of HTTP commands are handled by
    the single "handle_any" method above.

    """

    print("handle_one_request");
    try:
      self.raw_requestline = self.rfile.readline(65537)
      if len(self.raw_requestline) > 65536:
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.send_error(414)
        return
      if not self.raw_requestline:
        self.close_connection = 1
        return
      if not self.parse_request():
        # An error code has been sent, just exit
        return
      self.handle_any();
      self.wfile.flush() #actually send the response if not already done.
    except socket.timeout as e:
      #a read or a write timed out.  Discard this connection
      self.log_error("Request timed out: %r", e)
      self.close_connection = 1
      return


  ##############################################################################

  def write_attributes( self, fp ):
    """
    Write all the attributes of the object self to the file pointer fp.
    Useful for debuggin.
    """

    fp.write( 'attributes\n' );
    fp.write( '==========\n' );
    for key in sorted( self.__dict__ ):
      fp.write( "%s: %s\n" % (repr(key),repr(self.__dict__[key]) ) );
    fp.write( '\n' );

  ##############################################################################

  def write_headers( self, fp ):
    """
    Write all the headers of the object self to the file pointer fp.
    Useful for debugging.
    """
    fp.write( 'headers\n' );
    fp.write( '=======\n' );
    for key in sorted( self.headers.keys() ):
      fp.write( "%s: %s\n" % (repr(key),repr(self.headers[key]) ) );
    fp.write( '\n' );

  ##############################################################################

  def form_test( self, fp ):
    """
    Write HTML code for a simple form to the file pointer, fp.
    """
    fp.write( '<FORM METHOD="post"><INPUT TYPE="text" NAME="key"/><INPUT TYPE="Submit"/></FORM>\n' );

################################################################################

if __name__ == '__main__':

  # print startup message
  sys.stderr.write( 80*"#"+"\n" );
  sys.stderr.write( "%s, (C) %s\n" % ( server_version, \
                                       SVN_INFO['Date'][-5:-1]) );
  sys.stderr.write( "  %s\n" % (SVN_INFO['HeadURL'],) );
  sys.stderr.write( "  SVN Revision: %s (%s, %s [%s])\n" % (
                       SVN_INFO['Revision'],
                       SVN_INFO['Date'][27:-1],
                       SVN_INFO['Date'][11:19],
                       SVN_INFO['Author'],) );
  sys.stderr.write( 80*"#"+"\n" );
  sys.stderr.flush();

  # fork a second process
  if os.fork()==0:
    # child process - RUNS HTTP
    server_address = ( SnakeCharmer_config.HTTP_WEB_ADDRESS, SnakeCharmer_config.HTTP_PORT ); # (address, port)
    httpd = SnakeCharmerServer(server_address, SnakeCharmerHandler);
    sa = httpd.socket.getsockname();
    print( "Process", os.getpid(), "serving HTTP on", sa[0], 
           "port", sa[1], "...");
    try:
      httpd.serve_forever();
    except KeyboardInterrupt as e:
      sys.stderr.write( "KeyboardInterrupt detected %d\n" % (os.getpid()) )
      sys.stderr.write( "Thank you, and good night!\n" );
  else:
    # parent process - RUNS HTTPS
    server_address = ( SnakeCharmer_config.HTTPS_WEB_ADDRESS, SnakeCharmer_config.HTTPS_PORT ); # (address, port)
    httpd = SecureSnakeCharmerServer(server_address, SnakeCharmerHandler);
    sa = httpd.socket.getsockname();
    print( "Process", os.getpid(), "serving HTTPS on", sa[0], 
           "port", sa[1], "...")
    try:
      httpd.serve_forever();
    except KeyboardInterrupt as e:
      sys.stderr.write( "KeyboardInterrupt detected %d\n" % (os.getpid()) )
      sys.stderr.write( "Thank you, and good night!\n" );
      os.wait();
    

