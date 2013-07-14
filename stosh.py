#!/usr/bin/python3

import sys;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);

import re;	# regular expression library for parsing command line
import os;
import pwd;
import cmd;
import time;		# time time-code dump filenames
import string;
import getpass;
import pstorage;
import readline;	# to manage tab completion and command history
import tempfile;
import traceback;

################################################################################
# SVN Info
################################################################################

svn_regex = re.compile( r'^\$[^:]*: (.*) \$$' );

SVN_INFO = {
  'Date': """$Date: 2011-03-18 09:57:25 -0400 (Fri, 18 Mar 2011) $""",
  'Revision': """$Revision: 2865 $""",
  'Author': """$Author: skremer $""",
  'HeadURL': """$HeadURL: https://www.kremer.ca/svn/Repository/Projects/SnakeCharmer/5.3/stosh.py $""",
  'Id': """$Id: stosh.py 2865 2011-03-18 13:57:25Z skremer $""",
  };

for key in SVN_INFO:
  SVN_INFO[ key ] = svn_regex.match( SVN_INFO[ key ] ).group(1);

# Note you must give the command:
#  svn propset svn:keywords "Date Revision Author HeadURL Id" stosh.py
# for this to work.

################################################################################

def pptraceback():
  """Pretty print traceback message."""

  for line in traceback.format_exception( *( sys.exc_info() ) ):
    sys.stderr.write( line );

################################################################################

def repr3( rstring ):
  """
  Generates a triple quoted repr with newlines unescaped.
  """

  # first do the usual escape
  estring = repr( rstring );

  quote = estring[0];
  text = estring[1:-1];

  text = text.replace( '\\n', '\n' ); # unescape new-lines

  return quote*3 + '\\\n' + text + quote*3;

################################################################################
################################################################################
################################################################################

class Interpreter( cmd.Cmd ):
  """
  This class represents a storage shell.  It provides a command-line interface
  to the pstorage python module.
  """

  ##############################################################################

  def __init__( self ):
    """
    Initialize the shell.
    """

    cmd.Cmd.__init__( self );	# start by initializing the Cmd parent class

    self.user    = "nobody";     
    self.dummyip = "127.0.0.1";

    self.storage  = pstorage.Storage( self.dummyip );

    self.intro  = "\npstorage shell v.6.0, (C) 2008-2011\n" + \
                  "  %s\n" % (SVN_INFO['HeadURL'],) + \
                  "  SVN Revision: %s (%s, %s [%s])\n" % (
                     SVN_INFO['Revision'],
                     SVN_INFO['Date'][27:-1],
                     SVN_INFO['Date'][11:19],
                     SVN_INFO['Author'],);
    	# display a start-up string
    
    self.cwd = "storage";
    self.set_prompt();
    self.link_list = [ "pass;" ];

  ##############################################################################

  def __getattr__( self, attr ):
    """
    This method overrides the normal attribute access method for commands.
    Specificially, it first tries to find the attribute by the normal 
    mechanisms, but if that fails it looks in pstorage for the command.
    """
    try:
      return cmd.Cmd.__getattr__( self, attr );
    except AttributeError as e:
      pass;

    # could not find the attribute in this interpreter object or its class.
    # now look in pstorage.

    method = getattr( self.storage.Library.STOSH, attr );

    # this method's container (i.e. the object to which the method is applied)
    # is currently self.storage.Library.STOSH
    # but we would like it to be this Interpreter object.
    # so we use this ugly hack:

    method.__container__ = self;
    return method;

  ##############################################################################

  def onecmd( self, line ):
    """
    Copied and pasted from python source... added high level except line... 

    Interpret the argument as though it had been typed in response
    to the prompt.

    This may be overridden, but should not normally need to be;
    see the precmd() and postcmd() methods for useful execution hooks.
    The return value is a flag indicating whether interpretation of
    commands by the interpreter should stop.

    """

    self.storage.refresh();

    cmd, arg, line = self.parseline( line );	# strip whitespace from the line
                                                # collect all valid IDENTCHARS
						#   into cmd
						# strip the rest and store 
						#   in a string called arg
						# save return the original line
						#   as a string called line
						# ! is replaced by 'shell '
						# ? is replaced by 'help '
						# returns None, None, line 
						#   if something fails

    if not line:
      result = self.emptyline();	# do what you normally do if the user 
					# hits return

    if cmd is None:		# if you couldn't parse it
      result = self.default( line );	# do the usual

    self.lastcmd = line;	# remember the command for later

    if cmd == '':		# if command was blank
      result = self.default( line );	# do the usual

    try:
      import getpass;
      func = getattr( self, 'do_' + cmd );
      result = func( arg );
    except Exception as e:
      result = self.unexpected( line );

    return result;

################################################

  def unexpected( self, line ):
    sys.stderr.write( "*** Command %s throws unexpected Exception!\n" % line );
    pptraceback();
    return;

################################################

  def getuser( self ):
    while 1:
      sys.stdout.write( "Username: " );
      sys.stdout.flush();
      username = sys.stdin.readline();
      if re.match( r'[a-zA-Z_]*$', username ):
        return username.strip();

################################################

  def set_prompt( self ):
    self.prompt = "\n%s:%s\n$ " % ( self.user, self.cwd );
    	# set the prompt to something informative

################################################

  def remove_space( self, phrase ):
    result = '';
    for x in range( 0, len( phrase ) - 1 ):
      if phrase[x] != ' ':
        result += phrase[x];
    return result;

################################################
  def valid_path( self, path ):
    result = False;
    for x in range( 0, len( path ) - 1):
      if path[x] != ' ' and path[x] != '.':
        result = True;
    return result;

################################################
  def do_EOF( self, args ):
    """
    Quit the shell by sending and end of file response (Control-d).
    """
    self.quit();

################################################
  def do_exit( self, args ):
    """
    Quit the shell by typing "exit".
    """
    self.quit();

################################################
  def do_quit( self, args ):
    """
    Quit the shell by typing "quit".
    """

    self.quit();

################################################
  def quit( self ):
    sys.stdout.write( '\n' );
    readline.write_history_file( os.path.expanduser( "~/.stosh_history" ) );
    exit( 0 );

################################################


if __name__ == '__main__':
  # if this code is being run as an executable
  readline.set_completer_delims(' \t\n');

  try:
    readline.read_history_file( os.path.expanduser('~/.stosh_history') );
  except IOError as e:
    open( os.path.expanduser('~/.stosh_history'), 'w' ).close();	
		# create empty file
    pass;

  interp = Interpreter(); # initialize the interpreter
  interp.cmdloop();     # accept commands

