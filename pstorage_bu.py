# pstorage.py

import sys;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);

import re;
import os;
import pwd;
import time;
import types;
import socket;
import marshal;
import datetime;	# required by date returned from database

import traceback;
from functools import reduce
try:
  from mod_python import apache;
except ImportError as e:
  pass;


import storserv_config;

################################################################################

"""
This module defines a set of replacement objects for built in python types 
in such a way that calls to those objects will initiate communication with 
a database to retrieve necessary information.  The replacements for built in 
types (e.g. Dictionary, List) should eventually strictly conform to the 
replaced Python objects' interfaces and tested using Python's build-ins' 
regression testing.
"""


################################################################################

################################################################################
# get information about the last exception and send it to the error log.

def log_exception():
  """
  Print a formatted exception report for the last exception to the apache 
  error log.
  """
  for line in traceback.format_exception(*(sys.exc_info() )):
    sys.stderr.write( line );


################################################################################

REGEX_GET_METHOD_NAME = re.compile( """\s*def\s+(([^ \(])*)""" );

################################################################################
# Exceptions that can be raised by this module.
################################################################################

class StorservSyntaxError( Exception ):
  def __init__( self, args=None ):
    self.args = (args,);

################################################################################

class SCAccessException(Exception):
  '''
  Convenience exception intentionally raised due to a message from the database indicating access was denied.
  '''
  def __init__(self, obj_key, action, user):
    self.obj_key = obj_key;
    self.action = action;
    self.user = user;
    self.value = 'permission denied';

  def __str__(self):
    if self.obj_key:
      self.obj_key = 'storage.'+self.obj_key;
    else:
      self.obj_key = 'storage';
    return '%s (%s) %s.%s' % (self.value,self.user,self.obj_key,self.action,);

################################################################################

class SCLoginException(Exception):
  '''
  Convenience exception intentionally raised due to a message from the database indicating access was denied.
  '''
  def __init__(self, old_user, new_user):
    self.old_user = old_user;
    self.new_user = new_user;
    self.value = 'Permission denied';

  def __str__(self):
    return '%s for user %s to login as %s' % ( self.value,
                                               self.old_user,self.new_user,);

################################################################################
# this class should be moved out of pstorage (since it is not an integral
# part of pstorage; i.e. pstorage could conceivably be used in another 
# application which would have no need of a PageController), but this
# causes the PageController object not to be found when methods are evaluated
# within the scope of pstorage - need to find an elegant solution to this

class PageController:
  """
  This is a PageController class that facilitates rendering of web-pages.
  It provides a target object for python's string subsitution operator "%"
  that reteives attributes from the web_site, layout or page object.
  It also calls methods from said objects and returns their values.
  """

  def __init__( self, req, page ):
    self.req         = req;
    #self.site        = req.web_site;
    #self.site_path   = '';
    #self.layout      = req.web_site.layout;
    self.page        = page;
    #self.page_path   = os.path.splitext(req.uri)[0];
    #if self.page_path == '/':
    #  self.page_path = '/index';

  def __str__( self ):
    return self.layout.html % self;

  def __getitem__( self, key ):
    try:
      target = eval( 'self.' + key );
    except AttributeError as e:
      # could not find it directly, so try in page, layout and site 
      # (in that order)
      try:
        target = eval( 'self.page.' + key );
      except AttributeError as e:
        try:
          target = eval( 'self.req.ps_site.' + key );
        except AttributeError as e:
          raise AttributeError("neither %s nor %s have attribute '%s'" \
                % (self.page.canonicalname(),
                   self.req.ps_site.canonicalname(),
                   key));

    if isinstance( target, Method ):
      target = target( self.req );
    try:
      target = target.replace( '%"', '%%"' );
      return target % self;
    except (ValueError, AttributeError) as e:
      raise "%s %s %s\n" % (e, repr(target), repr(self) );
    

##############################################################################

def recv( conn ):
  """
  This function receives data over the connection.  The data is read
  in MAX_MESSAGE_SIZE blocks of characters.  If the last character received
  is not the EOT character, then additional blocks are read and appended.
  """

  message = '';

  while True:
    message += conn.recv( storserv_config.MAX_MESSAGE_SIZE ).decode('UTF-8');
    if message[-1]==storserv_config.EOT:
      break;
  return message[:-1];

################################################################################
# pstorage types
################################################################################

class PStorBaseObject( object ):
  """
  Abstract class which defines a set of methods which all classes within the 
  module should inherit.
  """

  # here are some reserved words
  __reserved__ = [
  # reserved attributes
  '__reserved__',
  '__key__',
  '__connection__',
  '__root__',
  '__container__',
  # reserved methods
  'canonicalname',
  'Dict',
  'List',
  'uri2py',
  'islink',
  '__eq__',
  ];


  ##############################################################################

  def Dict( self, key=None ):
    '''
    Convienience method to instantiate and then return a new Dict type object.
    '''
    return Dict( self.__connection__, key=key );


  ##############################################################################

  def List( self, key=None ):
    '''
    Convienience method to instantiate and then return a new List type object.
    '''
    return List( self.__connection__, key=key );

  ##############################################################################
  #class StorservException( Exception ):
  #  def __init__( self, args=None ):
  #    self.args = (args,);
  #########################


  def canonicalname( self, key=None ):

    if key==0:
      raise Exception('old key');
    if key==None:
      try:
        return self.__key__;
      except Exception as e: 
        return "???%s???", e;
  
    else:
      try:
        return key;
      except Exception as e:
        raise;
        return "???%s???", e;

  def __eq__( this, other ):
    if hasattr( other, '__key__' ):
      return (this.__key__ == other.__key__);
    else:
      return False;

  def uri2py( self, path ):
    return getattr( self, path );

  def islink( self ):
    return self.__connection__.db_islink( self.__key__ );

################################################################################
    
class Object( PStorBaseObject ):
  """
  This class represents a reference to any object that is mutable.
  """

  __reserved__ = PStorBaseObject.__reserved__ + [
  '__setattr__',
  '__delattr__',
  'getcontents',
  'getattributes',
  'getncontents',
  'getnrcontents',
  'hasattr',
  '__getattribute__',
  '__str__',
  '__repr__',
#  'keys',
  '__init__',
  'Method',
  ];


  def __init__( self, connection, key ):
    """
    Creates a reference object that refers to a mutable object in the
    persistent storage system.
    """
    self.__key__ = key;
    self.__connection__ = connection;
  

  def __delattr__( self, attr ):
    self.__connection__.db_delattr( self.__key__, attr );

  def hasattr( self, attr ):
    return self.__connection__.db_hasattr(self.__key__,attr);

  def getattributes( self ):
    """
    Return a list of this object's attributes' names.
    """
    result = self.__connection__.db_getattributes(self.__key__);
    return result;

  def getcontents( self ):
    """
    Returns a list of tuples containing information about the object's 
    attributes.
    """
    result = self.__connection__.db_getcontents(self.__key__);
    return result;

  def getncontents( self ):
    return len(self.getcontents());

  def getnrcontents( self ):
    """
    Recursive count of contents.
    """
    my_contents = self.getcontents();
    return len( my_contents ) + reduce( lambda x,y: x+y, [ Object( self.__connection__, item ).getnrcontents() for item in my_contents if item!=None], 0 );

  def keys( self ):
    return self.__connection__.db_keys(self.__key__);

  def __str__( self ):
    return 'Object(%s)' % (repr(self.__key__));

  def update_handler( self, name ):
    pass;

  def __repr__( self ):
    return 'Object(%s)' % (repr(self.__key__),);

  def get__key__(self):
    return object.__getattribute__(self,"__key__");

  def __setattr__( self, name, value ):
    if name in self.__class__.__reserved__:
      object.__setattr__( self, name, value );

    else:
      if type(value)==type(None):
        self.__connection__.db_setattr( self.__key__, name, value ); 
        self.update_handler(name);
        return;

      if type(value)==type(True):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type(3):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type(3):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type(0.3):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type(""):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type(b''):
        self.__connection__.db_setattr( self.__key__, name, value );
        self.update_handler(name);
        return;

      elif type(value)==type([]):
        # create and attach new list
        # (call __setattr__ again with an empty pstorage List)
        setattr( self, name, List( self.__connection__, None ) );
        result = getattr( self, name );
        # add items to it

        result.extend( value );
        self.update_handler(name);
        return;

      elif type(value)==type({}):
        setattr( self, name, Dict( self.__connection__, None ) );
        result = getattr( self, name );

        result.update( value );
        self.update_handler(name);
        return;

      elif isinstance( value, File):
        self.__connection__.db_setattr( self.__key__, name, value );
        return;

      else:	# we are dealing with an object,
        if isinstance( value, PStorBaseObject ):
          self.__connection__.db_setattr( self.__key__, name, value );
          return;

        else:
          raise TypeError('Cannot assign python object to pstorage attribute.');


  def __getattribute__( self, attr, python_object=1 ):
    """
    Retrieves the given attribute, "attr", from the object referenced by "self".

    It should be noted that "self" is an object of class "Object".  This 
    object represents a reference to a virtual PersistentObject.  The virtual 
    PersistentObject is not an object in python, and does not explicitly exist 
    in the python interpreter.  Instead, the behaviours and contents of the  
    virtual PersistentObject are simulated by calls to the "Object".

    When accessing contents it is important to distinguish their locations
    within either python objects and classes or within virtual 
    PersistentObjects.

    Attributes can be found in one of the following places.

    1.  In the virtual PersistentObject.
    2.	In the virtual PersistentObject's "Class" (which is also
        a virtual PersistentObject and the virtual PersistentObject's 
	"Class"'s ancestry (which are also virtual PersistentObjects).
    3.  In the object or the object's "__class__" (which is a python
        class/object).

    The lookup of contents is generally done in the order 1,2,3 as indicated
    above.  Thus, the objects can provide default values/methods for
    PersistentObjects.
    """

    if attr=='__class__' or attr in self.__class__.__reserved__:
      return object.__getattribute__( self, attr );

    #####################################################################
    # 1. look for the attribute in the persistent object (database)
    try:
      result = self.__connection__.db_getattribute( self.__key__, attr );

      if type(result) in [ type(None), type(True), type(1), type(1), 
                           type(0.1), type(""), type(b"") ]:
        return result;

      else:
        result.__container__ = self;
        return result;

    except IndexError as e:
      # could not find the attribute in the persistent object
      if attr in repr( e ):
        pass;	# keep looking
      else:
        raise;
    except AttributeError as e:
      # could not find the attribute in the persistent object
      if attr in repr( e ):
        pass;	# keep looking
      else:
        raise;

    except RuntimeError as e:
      raise RuntimeError('Infinite Recursion:  %s.%s\n' % (
            object.__getattribute__( self, '__key__' ), attr ));

    #####################################################################
    # 2. look in persistent object's persistent class
    try:
      if attr!='Class':		# avoids infinite recursion
        pc = self.Class;	# get the persistent class
        result = getattr( pc, attr );
        
        if type(result) in [ type(True), type(1), type(1), type(0.1), type("") ]:
          return result;

        else:
          result.__container__ = self;
          return result;


    except IndexError as e:
      # didn't find the attribute in the object\'s persistent class
      pass;
    except AttributeError as e:
      pass;


    #####################################################################
    # 3. look in python object
    if python_object:
      # resort to trying to find it the old fashioned way (in the python object       # of Object class)
      try:
        return object.__getattribute__(self,attr);
      except AttributeError as e:
        pass;

    # if we just can't find it at all
    raise AttributeError("%s has no attribute '%s'" % ( repr(self.__key__),
                                                          attr ));

 
  def Method( self, key=None ):
    """
    """
    return Method( self.__connection__, key=key );	

  # def copy() - no copy in Object just like there is no copy in python 
  # objects





################################################################################

class Dict( PStorBaseObject ):
  """
  This class (attempts to) conform to the python dictionary interface but 
  rather than storing information within memory belonging to the python 
  interpreter calls to a database program allow for data to be stored 
  within a postgres DB.
  """

  __reserved__ = PStorBaseObject.__reserved__ + [
    '__len__',
    '__getitem__',
    '__setitem__',
    'getcontents',
    '__str__',
    '__repr__',
    '__delitem__',
    '__contains__',
    'iter',
    'clear',
    'copy',
    'fromkeys',
    'get',
    'has_key',
    'items',
    'keys',
    'values',
    'iteritems',
    'iterkeys',
    '__ne__',
    '__lt__',
    '__le__',
    '__gt__',
    '__ge__',
    'pop',
    'popitem',
    'update',
    'setdefault',
    '__init__',
  ];

  def __init__( self, connection, key ):
    """
    Creates a reference object that refers to a mutable object in the storage
    database.

    If a key is supplied, then the reference object is identified by this key
    and subsequent access to the reference object will retrieve information
    pertaining to the key from the database.

    If no key is supplied a new reference object is created and returned.
    """

    self.__key__ = key;
    self.__connection__ = connection;


  def __len__( self ):
    '''
    Returns the length of the dic as given by a DB call.
    '''
    return self.__connection__.db_len_dict(self.__key__);
 
  def __getitem__( self, key ):
    '''
    Returns the object specified by key.  Probably works, more testing required.
    '''
    result = self.__connection__.db_getitem_dict( self.__key__, key );
    if result==None:
      raise IndexError('Index %s does not exist in object %s (0x%x).' % \
      			(repr(key), self.canonicalname(self.__key__), self.__key__));
    # note: dict is included here for __getitem__ slice selections
    elif type(result) in [ type(True), type(1), type(1), type(0.1), type(""), type([]) ]:
      return result;
    else:
    # what?
      return result;

  def __setitem__( self, key, value ):
    # should this really return va value?
    '''
    Attempts to set the item given a key:value pair.  May cause a exception based upon permissions.
    '''
    if type(value).__name__=='instance' and not isinstance( value, File ):
      return self.__connection__.db_setitem_dict( self.__key__, key, \
                     value.__key__ );
    else:
      return self.__connection__.db_setitem_dict( self.__key__, key, value );


  #############################################################################
  def getcontents( self ):
    '''
    Returns the contents of the Dict recieved from DB.  Results should be cased as list of tuples.
    '''
    return self.__connection__.db_getcontents(self.__key__);

  def __str__( self ):
    '''
    Returns a string representation of the Dict which should be equivalent to the str repr of a python dict with the same key:value pairs (order is not defined)
    '''
    return 'Dict(%s)' % (repr(self.__key__),);

  def __repr__( self ):
    return 'Dict(%s)' % (repr(self.__key__),);

  def __delitem__( self, key ):
    self.__connection__.db_delitem_dict( self.__key__, key );

  def __contains__( self, obj ):
    result = self.as_dict();
    return obj in result.__iter__();

  def __iter__( self ):
    result = self.as_dict();
    return result.__iter__();

  def iter(self, d):
    return  d[:].__iter__;

  def clear(self):
    for key in list(self.keys()):
      self.__connection__.db_delitem_dict( self.__key__, key );

  def copy(self):
    """
    For dictionaries, the copy command creates a new, un-named dictionary
    containing the same values as the original which can then be assigned
    to something:

    e.g.  home.tmp.test2 = home.tmp.test.copy();

    It is not possible to create an unnamed persistent Dict.

    The work-around is a 2 step process.

    home.tmp.test2 = self.storage.Object();
    home.tmp.test2.update( home.tmp.test );
    """

    raise Exception("not possible");

  def as_dict(self):
    # return a dictionary of my items
    copy = {};
    for item in list(self.items()):
      copy[ item[0] ] = item[1];
    return copy;

  def fromkeys(self, seq, val=None):
    '''
      Create a new Dict object from a sequence of keys with values all equal to val (defaults to None)
      Note: A new Dict obj must have parent set  in the calling function as it will currently belong to root
    '''

    newd = self.__init__.Dict(0);
    for key in seq:
      newd[key] = val;
    return newd; 

  def get(self, key, default=None):
    '''
    Return the value for key if key is in the dictionary, else default. 
    If default is not given, it defaults to None, so that this method never 
    raises a KeyError.
    '''
    try:
      result = self.__getitem__( key );
      return result;
    except KeyError as e:
      return default;

  def has_key(self, key):
    try:
      result = self.__getitem__( key );
      return True;
    except KeyError as e:
      return False;
      
  def items(self):
    return self.__connection__.db_items(self.__key__);

  def keys(self):
    result = [];
    for item in list(self.items()):
      result.append( item[0] );
    return result;

  def values(self):
    result = [];
    for item in list(self.items()):
      result.append( item[1] );
    return result;

  def iteritems(self):
    return list(self.items()).__iter__();

  def iterkeys(self):
    return list(self.keys()).__iter__();

  def itervalues(self):
    return list(self.values()).__iter__();


  def __eq__( self, other ):
    if type( other ) != type ( {} ) and not isinstance( other, Dict ):
      return False;

    if len(self)!=len(other):
      return False;

    for key, value in list(self.items()):
      if value!=other[key]:
        return False;
    return True;
      
      
  def __ne__( self, other ):
    return not (self==other);

  def __lt__( self, other ):
    return sorted(self.items())<sorted(other.items());

  def __le__( self, other ):
    return sorted(self.items())<=sorted(other.items());

  def __gt__( self, other ):
    return sorted(self.items())>sorted(other.items());

  def __ge__( self, other ):
    return sorted(self.items())>=sorted(other.items());

  def pop(self, key):
    '''
    removes pair with the specified key from the dict and returns it. 
    '''
    if key in self:
      temp = self[key];
      del self[key];
      return key,temp;
    else:
      raise KeyError;

  def popitem( self ):
    '''
    removes one arbitrary pair from the dict and returns it. 
    TODO check for no keys in dict
    '''
    item = list(self.items())[0];
    return self.pop(item[0]);


  def update(self, other=None, **args ):
    ''' 
    '''

    if other:

      if type(other)==dict:
        for key,value in list(other.items()):
          self[key]=value;
         
      elif type(other)==iter:
        #keyword
        for key,value in other:
          self[key] = value;
  
    else: 
      #keyword
      for key,value in list(args.items()):
        self[key] = value;



  def setdefault(self, key, default=None):
    '''
    If key is in the dictionary, return its value. If not, insert key with a value of default and return default. default defaults to None.
    '''
    if key in self:
      return self[key];
    else:
      self[key] = default;
      return default;

################################################################################

class List( PStorBaseObject ):
  """
  This class represents a reference to a list.
  """

  __reserved__ = PStorBaseObject.__reserved__ + [
    '__len__',
    '__getitem__',
    '__setitem__',
    'getcontents',
    '__str__',
    '__repr__',
    'append',
    '__add__',
    '__delitem__',
    'extend',
    'count',
    'index',
    'insert',
    'pop',
    'remove',
    'reverse',
    'sort',
    '__contains__',
    '__iter__',
    '__eq__',
    '__ne__',
    '__gt__',
    '__ge__',
    '__lt__',
    '__le__',
    '__init__',
  ];

#  def __init__( self, connection, key=None, value=None ):
#    """
#    Creates a reference object that refers to a mutable object in the storage
#    database.
#
#    If a key is supplied, then the reference object is identified by this key
#    and subsequent access to the reference object will retrieve information
#    pertaining to the key from the database.
#
#    If no key is supplied a new reference object is created and returned.
#    """
#    self.__connection__ = connection;
#    if key is None:
#      # This is a reference to a new object
#      self.__key__ = self.__connection__.db_new_object();
#      if value:
#        for item in value:
#          self.append( item );
#    else:
#      # This is a reference to an existing object with the corresponding key
#      self.__key__ = key;

  def __init__( self, connection, key ):
    """
    Creates a reference object that refers to a mutable object in the
    persistent storage system.
    """
    self.__key__ = key;
    self.__connection__ = connection;
  
  def __len__( self ):
    return self.__connection__.db_len_list(self.__key__);
 
  def __getitem__( self, key ):
    if type(key)==type(0) and key<0:
      key=len(self)+key;

    result = self.__connection__.db_getitem_list( self.__key__, key );

    if type(key)==0 and not result:	# slices can return empty result
      raise IndexError('Index %s does not exist in object %s (0x%x).\n' % \
      			(repr(key), self.canonicalname(self.__key__), self.__key__));
    # note: list is included here for __getitem__ slice selections
    if type(result) in [ type(True), type(1), type(1), type(0.1), type(""), type([]) ]:
      return result;
    else:
      result.__container__ = self;
      return result;

  def __setitem__( self, index, value ):

    if index<0:
      index=len(self)-index;

    if type(value).__name__=='instance':
      return self.__connection__.db_setitem_list( self.__key__, index, \
                     value.__key__ );
    else:
      return self.__connection__.db_setitem_list( self.__key__, index, value );


  #############################################################################

  def getcontents( self ):
    return self.__connection__.db_getcontents(self.__key__);

  def __str__( self ):
    return 'List(%s)' % (repr(self.__key__));


  def __repr__( self ):
    return 'List(%s)' % (repr(self.__key__));

  def append( self, value ):
    self.extend( [value] );

  def __add__( self, other ):
    return db_append_list( self, other );

  def __delitem__( self, key ):
    if key<0:
      key=len(self)+key;

    self.__connection__.db_delitem_list( self.__key__, key );

  def extend( self, list2 ):
    # python implementation - this could be replaced by a servers-side
    # implementation which would be more efficient 
    # this implementation requires a lot of calls to "storserv"

    if isinstance(list2,List):	# if argument is a pstorage List object
      list2 = list2[:];		# convert it to a python list

    self.__connection__.db_extend_list( self.__key__, list2 );

    return self;

  def count( self, item  ):
    return self[:].count( item );

  def index( self, item, start=None, end=None ):
    pylist = self[:];

    # this is to overcome an error in the index method which does not accept
    # None as an argument
    #
    # e.g. 
    # >>> [1,2,3].index(2,None,None)
    # Traceback (most recent call last):
    #   File "<stdin>", line 1, in <module>
    # TypeError: slice indices must be integers or None or have an __index__ 
    # method
    if end is None:
      if start is None:
        return pylist.index( item );
      else:
        return pylist.index( item, start );
    else:
      return pylist.index( item, start, end );

  #############################################################################
  def insert( self, index, value ):
    return self.__connection__.db_insert( self.__key__, index, value );

  #############################################################################
    
  def pop( self, index=-1 ):
    result = self[index];
    del self[index];
    return result;

  def remove( self, item ):
    del self[ self.index(item) ];

  def reverse( self ):
    self.__connection__.db_reverse( self.__key__ );

  def sort( self, key=None, reverse=False ):
    # this implementation is slow - but faithful to python
    # it does the actual sort in python on a copy of the list
    pylist = self[:];
    pylist.sort( key=key, reverse=reverse );

    while len(self):
      self.pop();
    self.extend( pylist );


  def __contains__( self, obj ):
    result = self[:];
    return obj in result.__iter__();

  def __iter__( self ):
    result = self[:];
    return result.__iter__();

  def __eq__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]==other;

  def __ne__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]!=other;
   
   
  def __gt__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]>other;

  def __ge__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]>=other;

  def __lt__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]<other;
   
  def __le__( self, other ):
    if isinstance( other, List ):
      other = other[:];
    return self[:]<=other;
  
################################################################################

class Method( Object ):
  __reserved__ = Object.__reserved__ + [
    'compile',
    '__call__',
  ];

  def __repr__( self ):
    return 'Method(%s)' % (repr(self.__key__),);

  def __str__( self ):
    return 'Method(%s)' % (repr(self.__key__));

  def compile( self ):
    try:
      self.method_name = REGEX_GET_METHOD_NAME.match( str(self.method_text) ).group(1);
    except Exception as e:
      raise SyntaxError("Method delcaration does not match \"def method_name( ... )\"");

    try:
      exec( self.method_text );
      function = eval( str(self.method_name) );
      self.marshalled_code_object = repr( marshal.dumps( function.__code__ ) );
      self.__defaults__ = repr( function.__defaults__ );
      self.errors = None;
    except Exception as e:
      self.errors = ''.join( traceback.format_exception(*(sys.exc_info())) );
      self.marshalled_code_object = "";

  def __call__( self, *args, **keyargs ):
    #if self.errors:
    #  raise SyntaxError, self.errors;

    code_string = eval(self.marshalled_code_object);

    code_object = marshal.loads( code_string );

    function = types.FunctionType( code_object, globals(), None, 
                                   eval( self.__defaults__ ) );

    function_result = function( *([self.__container__]+list(args)), **keyargs );

    return function_result;

  def copy( self ):
    return Method( self.__root__, method_text = str(self.method_text) );


################################################################################

'''class Link( Object ):
  """
  This class represents a link to another referenced object.
  """
  __reserved__ = Object.__reserved__ + [
  ];

  def __init__( self, connection, key=None, referenced_object=None ):
    if key and not referenced_object:
      Object.__init__( self, root, key );
    elif referenced_object and not key:
      Object.__init__( self, root );
      self.__referenced_object_key__ = referenced_object.__key__;
    else:
      raise Exception, "Bad Method Initialization %s %s" % ( 
      					key, referenced_object );

  def __repr__( self ):
    return "storage.Link( reference_object=%s )" %  \
         ( Object( self.__root__, key=self.__referenced_object_key__ \
                 ).canonicalname() );


  def __getattribute__( self, attr ):
   
    if attr in ["__referenced_object_key__",'__root__','__key__','__class__','getcontents']:
      return Object.__getattribute__( self, attr );
    else:
      result = getattr(  Object( self.__root__, 
                                 key=self.__referenced_object_key__ ), attr );
      if type(result) in [ type(True), type(1), type(1L), type(0.1), type("") ]:
        return result;
      else:
        try:
          result.__container__ = self;
        except AttributeError, e:
	  # AttributeError: 'instancemethod' object has no attribute 
          #             '__container__'
          pass;
        return result;

  def __iter__( self ):
    ro = List( self.__root__, key=self.__referenced_object_key__ );
    return ro.__iter__();

  def islink( self ):
    return True;'''

################################################################################

class File():

    def __init__( self, content, content_type):
      self.content_type = content_type;
      self.content = content;

    def __repr__( self ):
      return 'File( ' + repr(self.content) + ', ' + repr(self.content_type) + ' )';

    def getcontent( self, req ):
      req.content_type = self.content_type[0];
      req.content = self.content;

################################################################################

class Storage( Object ):
  """
  This class represents a connection to the root object 
  in the persitent storage system.  This connection will have an
  associated sessionID and storserv generates password hash for authentication.

  It has the following attributes:
    __key__ - key value in the database for this object (fixed at zero)
    __socket_name__ - the filename of the socket used to communicate
                      with storserv
    __root__ - reference to the root object (which is this)
    __sessIP__ - IP address associated with the current session connection
    __sessID__ - ID number of the current session
    __hashID__ - password hash for the current session (assigned by the server)
  """

  __reserved__ = Object.__reserved__ + [
  '__socket_name__',
  '__sessIP__',
  '__sessID__',
  '__hashID__',
  '__username__',
  'login',
  'refresh',
  'raise_SCAccessException',
  'raise_SCLoginException',
  'raise_StorservException',
  'Object',
  'Link',
  'db_items',
  'db_hasattr',
  'db_command',
  'db_getcontents',
  'db_getattributes',
  'db_new_object',
  'db_new_string',
  'db_setattr',
  'db_setitem_list',
  'db_len_list',
  'db_len_dict',
  'db_getattribute',
  'db_getitem_list',
  'db_delitem_list',
  'db_getattrname',
  'db_getstring',
  'db_delattr',
  'db_insert',
  'db_reverse',
  'db_sort',
  'db_dellink',
  'db_dellinkto',
  'db_keys',
  'db_hasattr',
  'db_getcanonicalname',
  'db_copy',
  'db_setitem_dict',
  'db_getitem_dict',
  'db_delitem_dict',
  ];

  def __init__( self, sessIP=None, sessID=None, hashID=None ):
    """
    This is the constructor for the connection to the top level persistent
    storage object.

    The following optional parameters can be supplied:
       sessIP - a string containing the IP address associated with the 
                connection session (this should be suppied by the creating
                code if possible)
       sessID - a string containing the sessionID of an existing session, or
                None, if this is a new session
       hashID - a string containing the storserv generated hash-code associated
                with the existing session, or None, if this is a new session
    """

    self.__key__ = '';	# have to do this before trying to access any 
                        # other contents, key = '' indicates the top level 
                        # object, root in the filesystem-like hierarchy

    # this IS the root - supplied for backward compatability with Object
    # objects

    # now call Object's constructor
    Object.__init__( self, 
                     StorservConnection( sessIP, sessID, hashID ), 
                     key='' );



  def refresh( self ):
    """
    Get fresh values of __sessID__, __hashID__, and __username__.
    This is useful for the __hashID__ which contains a time stamp that 
    is defined modulo storserv_config.SESSION_INACTIVITY and is valid for 
    two intervals.  By refreshing the storage connection at least once
    during each interval, the __hashID__ can be kept valid indefinately.
    """
    self.__sessID__, self.__hashID__, self.__username__ = \
         self.__connection__.db_command( 'get_session_info', str(-1) );

  ##############################################################################
  def login( self, username, password ):
    """
    Request validation of username and password from storserv
    upon success, session in DB will be updated and future requests 
    from client will have appropritate access
    """
    new_username = self.__connection__.db_command( 'login', 
                                                   '', 
                                                   self.__connection__.__sessID__, 
                                                   username, password );
    self.__connection__.__username__ = new_username;
    return new_username;

  ##############################################################################
  def logout( self ):
    """
    Logout (by logging in as "nobody")
    """
    return self.__connection__.db_command( 'login', self.__sessID__,'nobody', '' ); # no password required
    
  ##############################################################################

  def create_user( self, new_user, new_pass ):
    return self.__connection__.db_command( 'create_user', new_user, new_pass );

  ##############################################################################

  def modify_user( self, new_user, new_pass ):
    return self.db_command( 'modify_user', new_user, new_pass );

  ##############################################################################

  def authenticate( self ):
    self.db_command( 'authenticate', self.__sessIP__, self.__sessID__, self.__hashID__ );

  ##############################################################################

  def Object( self, key=None ):
    return Object( self.__connection__, key );

  ##############################################################################

  def Link( self, key=None ):
    return Link( self.__connection__, key );

  ##############################################################################

  def File( self, value=None ):
    return File( self.__connection__, value );

  ##############################################################################

class StorservConnection:

  def __init__( self, sessIP, sessID, hashID ):
    # check if there is a PID_FILE
    if not os.path.exists(storserv_config.PID_FILE):
      raise Exception("PID_FILE %s not found.  Is storserv running?" % \
                       storserv_config.PID_FILE);

    # read the pid
    pid_file = open( storserv_config.PID_FILE );
    pid = int( pid_file.read() );
    pid_file.close();

    # determine socket file name
    self.__socket_name__ = storserv_config.SOCKET_PATH;

    # record constructor parameters
    self.__sessIP__ = sessIP;
    self.__sessID__ = sessID; 
    self.__hashID__ = hashID; 

    self.__sessID__, self.__hashID__, self.__username__ = \
         self.db_command( 'get_session_info', str(sessID) );

  ##############################################################################

  def db_command( self, command, *args, **vargs ):
    # Communicate with storserve through socket
    comm = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM );
    try:
      comm.connect( self.__socket_name__ );
    except socket.error as e:
      log_exception();
      raise Exception( 'Error: could not connect to server socket %s\n' % self.__socket_name__ );

    string = repr( ('a',command,self.__sessIP__,self.__sessID__,self.__hashID__,args,vargs) );
    comm.send( bytes(string + storserv_config.EOT,'UTF-8') );
    reply = recv(comm);

    try:
      # evaluate and return output
      return eval( reply );

    except SCAccessException as e:
      raise;
    except Exception as e:
      raise;

  ##############################################################################

  def db_islink( self, key ):
    return self.db_command( 'islink', key );

  def db_items( self, key ):
    return self.db_command( 'items', key );

  def db_getcontents( self, key ):
    # calls to the database access method
    return self.db_command( 'getcontents', key );
  
  def db_getattributes( self, key ):
    return self.db_command( 'getattributes', key );

  def db_new_object( self ):
    # A new object has been referenced, the object must be instantiated in our DB.
    return self.db_command( 'new_object', 0 );

  def db_new_string( self, value ):
    return self.db_command( 'new_string', 0, value );

  def db_setattr( self, parent, name, child ):
    self.db_command( 'setattr', parent, name, child );
    return child;

  def db_setitem_list( self, parent, name, child ):
    return self.db_command( 'setitem_list', parent, name, child );

  def db_extend_list( self, list1, list2 ):
    return self.db_command( 'extend_list', list1, list2 );

  def db_len_list( self, thelist ):
    return self.db_command( 'len_list', thelist );

  def db_len_dict( self, thedict ):
    return self.db_command( 'len_dict', thedict );

  def db_getattribute( self, key, attr_name ):
    try:
      result = self.db_command( 'getattribute', key, attr_name );

      return result;
    except AttributeError as e:
      raise AttributeError('Attribute %s does not exist in object %s.\n' % \
      			(attr_name, key));

  def db_getitem_list( self, key, key_name ):
    result = self.db_command( 'getitem_list', key, key_name );
    return result;

  def db_delitem_list( self, key, key_name ):
    result = self.db_command( 'delitem_list', key, key_name );
    return result;

  def db_getattrname( self, key ):
    result = self.db_command( 'getattrname', key );
    return result;

  def db_getstring( self, key ):
    # changed to accomidate socket wrapper 5.1
    # return self.db_command( 'getstring', key );
    return self.db_command( 'getstring', key );

  def db_delattr( self, key, attr_name ):
    return self.db_command( 'delattr', key, attr_name );

  def db_insert( self, key, index, value ):
    return self.db_command( 'insert', key, index, value );

  def db_reverse( self, key ):
    return self.db_command( 'reverse', key );

  def db_sort( self, key ):
    raise Exception("Not implemented");
    return self.db_command( 'sort', key );

  def db_dellink( self, key, attr_name ):
    return self.db_command( 'dellink', key, attr_name );

  def db_dellinkto( self, key ):
    return self.db_command( 'dellinkto', key );

  def db_keys( self, key ):
    raise Exception('not implemented');

  def db_hasattr( self, key, attr_name ):
    return self.db_command( 'hasattr', key, attr_name );

  def db_getcanonicalname( self, key ):
    raise Exception('deprecated');

  def db_copy( self, key ):
    return self.db_command( 'copy', key );


  def db_setitem_dict( self, parent, name, child ):
    return self.db_command( 'setitem_dict', parent, name, child );

  def db_getitem_dict( self, key, key_name ):
    result = self.db_command( 'getitem_dict', key, key_name );
    return result;

  def db_delitem_dict( self, key, key_name ):
    result = self.db_command( 'delitem_dict', key, key_name );
    return result;
  ##############################################################################
  def raise_SCAccessException( self, obj_key, action, user):
    raise SCAccessException( obj_key, action, user);

  ##############################################################################
  def raise_SCLoginException( self, old_user, new_user ):
    raise SCLoginException( old_user, new_user );

  ##############################################################################
  def raise_StorservException( self, etype, pptraceback ):
    raise etype( pptraceback );

