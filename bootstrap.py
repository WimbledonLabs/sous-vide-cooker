#!/usr/bin/python3

import sys;
import getpass;
import pstorage;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);

# bootstrap python 3 compatible versions of the stosh functions into
# storserv_data

method_list = [ \
('do_cd',
r'''
def do_cd( self, args ):
  path = args;
  if path=='':        # no argument provided
    path = 'storage';

  else:
    #Get the path
    if path=='..':
      path = reduce( lambda x,y: x + '.' + y, self.cwd.split('.')[0:-1] );

    elif not self.valid_path( path ):
      sys.stderr.write( "-stosh: cd: Invalid argument '%s'" % path );
      return;

    elif path[0]=='[':
      path = self.cwd + path;

    else:
      path = self.cwd + '.' + path;

  #Remove anything that may break the path
  if path[-1] == '.':
    path = path[0:-1];

  #Make sure the path exists
  try:
    eval( 'self.' + path );
    self.cwd = path;
    self.set_prompt();
    return;

  except AttributeError as e:
    sys.stderr.write( "-stosh: cd: Directory does not exist" );
    sys.stdout.write( "\nWould you like to create the directory?(y/n): " );
    choice = ( sys.stdin.readline().split() )[0];
    if choice == 'y':
      #Create the directory
      return self.do_mkpath( args );
    return;
  return;
'''),
('do_compile',
r'''
def do_compile( self, args ):
  """
  """
  name = args;
  data = eval( 'self.'+self.cwd+'.'+name );

  data.compile();
  if data.errors:
    print( data.errors );
'''),
('do_edit',
r'''
def do_edit( self, args ):

  import tempfile;

  name = args;

  file_name = tempfile.mktemp();

  data = eval( 'self.'+self.cwd+'.'+name );

  data_type = type( data );

  if data_type.__name__ in ['Object', 'Dictionary', 'List']:
    print( "Can't edit %s" % data.__class__ );
    return;

  elif data_type.__name__=='Method':
    # have to fix name
    self.do_edit(args+'.method_text');
    self.do_compile(args);
    return;

  fp = open( file_name, 'w' );
  fp.write( str( data ) );
  fp.close();

  #Get the editor
  try:
    editor_name = os.environ['EDITOR'];
  except KeyError as e:
    sys.stderr.write( "-stosh: edit_str: You must define the environment variable \"EDITOR\" in your shell.\n" );
    sys.stderr.write( "Enter editor name: " );
    editor_name = sys.stdin.readline().strip();
    os.environ['EDITOR'] = editor_name;

  #Open the file in an editor and save the changes made by the user
  os.system( editor_name + ' ' + file_name );

  #Open the editor and take user input
  fp = open( file_name );                     #Open the file
  data = data_type( fp.read() );               #Read the contents of the file
  fp.close();

  # os.unlink( file_name );

  path = '.'.join( [ 'self', self.cwd ] + name.split('.')[:-1] );
  attrib = name.split('.')[-1];

  print( path, attrib );
  setattr( eval(path), attrib, data );
'''),
('do_ls',
r'''
def do_ls( self, args ):
  """
  List command.
  args can be a string indicating a path to the object that is supposed to
  be listed.
  """

  import pstorage;

  args.split();
  # self.cwd starts with storage....
  #Get the path and set the cmd
  if len(args)==0:
    path = 'self.' + self.cwd;
    cmd = path + ".getcontents()";

  elif len(args)==1:
    #print( "Before fix_path", args[-1] );
    path = self.fix_path(args[-1])
    cmd = path + ".getcontents()";

  elif len(args)==2:
    path = self.fix_path(args[-1])
    cmd = path + ".getcontents()";

  else:
    sys.stderr.write( "-stosh: ls: Too many arguments" );
    return;

  parent = eval(path);

  print( parent, ":" );

  try:
    mylist = eval( cmd );

    #Get the attributes and build the table
    for a in mylist:

      item_name = os.path.basename(a);
      item = eval(path+'.'+item_name);
      item_type = type( item ).__name__;
      item_value = repr( item ); 

      print( '%-25s %-10s %-40s ' % (item_name,item_type,item_value[0:40],) );


  except pstorage.SCAccessException as e:
    sys.stderr.write( "-stosh: ls: Access denied by host for path [%s]" % path );
    return;

  except AttributeError as e:
    sys.stderr.write( "-stosh: ls: Bad directory name" );
    sys.stderr.write( reduce( lambda x,y: x+y, traceback.format_exception( *( sys.exc_info() ) ) ) );
    return;

  except SyntaxError as e:
    pptraceback();
    sys.stderr.write( "-stosh: ls: Malformed directory name" );
    return;
  return;
'''),
('do_make',
r'''
def do_make( self, args ):

  type, name = args.split();

  if type=='None':
    setattr( eval('self.'+self.cwd), name, None );

  elif type=='int':
    setattr( eval('self.'+self.cwd), name, 0 );

  elif type=='float':
    setattr( eval('self.'+self.cwd), name, 0.0 );

  elif type=='complex':
    setattr( eval('self.'+self.cwd), name, 0J );

  elif type=='bool':
    setattr( eval('self.'+self.cwd), name, True );

  elif type=='str':
    setattr( eval('self.'+self.cwd), name, '' );

  #elif type=='list':
  #  setattr( eval('self.'+self.cwd), name, [] );

  elif type=='tuple':
    setattr( eval('self.'+self.cwd), name, (0,) );

  #elif type=='range':
  #  setattr( eval('self.'+self.cwd), name, range(0,10) );

  #elif type=='xrange':
  #  setattr( eval('self.'+self.cwd), name, xrange(0,10) );

  else:
    if type not in ['Object','List','Method','Dict']:
      print( 'Invalid type:  %s' % type );
      return;

    if type=='Method':
        setattr( eval('self.'+self.cwd), name, eval('self.storage.'+type)() );
        setattr( eval('self.'+self.cwd+'.'+name), 'method_text', 'def '+name+'( self, args ):' );
        setattr( eval('self.'+self.cwd+'.'+name), 'method_name', name );
    else:
                setattr( eval('self.'+self.cwd), name, eval('self.storage.'+type)() );
'''),
('do_rm',
r'''
def do_rm( self, args ):
  name = args;
  target = eval( 'self.'+self.cwd );
  delattr( target, name );
'''),
('do_su',
r'''
def do_su( self, username = '' ):  # optional commands should be implemented  
  import getpass;

  #Get the username and login information
  if username == '':
    username = self.getuser();
  password = getpass.getpass();

  #Log the user in
  try:
    self.storage.login( username, password );
    self.user = self.storage.__connection__.__username__;
    self.set_prompt();
    return;

  except pstorage.SCAccessException as e:
    sys.stderr.write( "-stosh: su: Access Denied. Please enter the correct password for user: '%s'" % ( username ) );
    return;
  return;
'''),
];

if __name__ == '__main__':

  password = getpass.getpass( "Enter root password: " );

  storage = pstorage.Storage( '127.0.0.1' );
  storage.login( 'root', password );

  for method_name,method_text in method_list:
    print( method_name );
    setattr( storage.Library.STOSH, method_name, storage.Method() );
    method = getattr( storage.Library.STOSH, method_name );
    method.method_text = method_text;
    method.compile();

    

