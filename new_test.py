#!/usr/bin/python3

import sys;

# check version number
if sys.version_info[0] < 3:
  sys.stderr.write( sys.argv[0] + " requries Python 3.0+\n" );
  sys.exit(-1);

import os;
import getpass;
import pstorage;
import storserv_config;

import unittest;

################################################################################

class Test01Connection( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );

  def test_01_username( self ):
    self.assertEqual( self.storage.__connection__.__username__, 'nobody' );

  def test_02_sessID( self ):
    self.assertTrue( int(self.storage.__connection__.__sessID__)>=0 );

  def test_03_hashID( self ):
    self.assertTrue( len(self.storage.__connection__.__hashID__)==40 );

################################################################################

class Test02BadPasswordLogin( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );

  def test_01_exception( self ):
    self.assertRaises( pstorage.SCLoginException, 
                       self.storage.login, 'root', 'password' );

################################################################################

class Test03GoodPasswordLogin( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_01_username( self ):
    self.assertEqual( self.storage.__connection__.__username__, 'root' );

  def  test_02_sessID( self ):
    self.assertTrue( int(self.storage.__connection__.__sessID__)>=0 );

  def test_03_hashID( self ):
    self.assertTrue( len(self.storage.__connection__.__hashID__)==40 );

################################################################################

class Test04BadUserLogin( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );

  def test_01_exception( self ):
    self.assertRaises( pstorage.SCLoginException, 
                       self.storage.login, 'bgates', 'password' );

################################################################################

class Test05Logout( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

    self.old_sessID = self.storage.__connection__.__sessID__;

    self.storage.login( 'nobody', '' );

  def test_01_username( self ):
    self.assertEqual( self.storage.__connection__.__username__, 'nobody' );

  def  test_02_sessID( self ):
    self.assertEqual( int(self.storage.__connection__.__sessID__), int(self.old_sessID) );

################################################################################

class Test06BadAccess( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );

  def test_01_access_root_password( self ):
    #self.assertRaises( pstorage.SCAccessException,
    #                   eval, 
    #                   'self.storage.' + storserv_config.USERS_OBJECT + \
    #                   '[%s]' % (repr('root'),) );
    self.assertRaises( pstorage.SCAccessException,
                       getattr,
                       (self.storage, '')
                       


################################################################################

class Test07Object( unittest.TestCase ):

  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );
   
  def test_01_getcontents( self ):
    self.assertEqual( type( self.storage.getcontents() ), type( [] ) );

  def test_02_not_empty( self ):
    self.assertTrue( len( self.storage.getcontents() )>0 );

  def test_03_make_objects( self ):
    # find home directory of root user
    home = self.storage.Server.Users['root'];

    # create new object called tmp in home directory
    home.tmp = self.storage.Object();

    self.assertTrue( home.tmp!=None );
    self.assertEqual( len( home.tmp.getcontents() ), 0 );

    home.tmp.a = self.storage.Object();
    home.tmp.b = self.storage.Object();
    home.tmp.c = self.storage.Object();

    self.assertEqual( len( home.tmp.getcontents() ), 3 );
    self.assertEqual( home.tmp.getncontents(), 3 );
    self.assertEqual( home.tmp.getnrcontents(), 3 );

  def test_04_make_nested_objects( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    self.assertTrue( home.tmp!=None );
    self.assertEqual( len( home.tmp.getcontents() ), 0 );

    home.tmp.a = self.storage.Object();
    home.tmp.a.b = self.storage.Object();
    home.tmp.a.b.c = self.storage.Object();

    self.assertEqual( len( home.tmp.getcontents() ), 1 );
    self.assertEqual( home.tmp.getncontents(), 1 );
    self.assertEqual( home.tmp.getnrcontents(), 3 );

  def test_05_syntax2_and_delete( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    self.assertTrue( home.tmp!=None );
    self.assertEqual( len( home.tmp.getcontents() ), 0 );

    home.tmp.a = self.storage.Object();
    home.tmp.a.b = self.storage.Object();
    home.tmp.a.b.c = self.storage.Object();

    self.assertEqual( len( home.tmp.getcontents() ), 1 );
    self.assertEqual( home.tmp.getncontents(), 1 );
    self.assertEqual( home.tmp.getnrcontents(), 3 );

    del home.tmp.a.b.c;
    del home.tmp.a.b;
    del home.tmp.a;

    self.assertEqual( len( home.tmp.getcontents() ), 0 );
    self.assertEqual( home.tmp.getncontents(), 0 );
    self.assertEqual( home.tmp.getnrcontents(), 0 );

  def test_06_add_repeat( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.a = self.storage.Object();
    home.tmp.a = self.storage.Object();
    home.tmp.a = self.storage.Object();

    self.assertEqual( len( home.tmp.getcontents() ), 1 );
    self.assertEqual( home.tmp.getncontents(), 1 );
    self.assertEqual( home.tmp.getnrcontents(), 1 );

  def test_07_repr( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    self.assertEqual( repr( home.tmp ),
                      'Object(%s)' % (repr(home.tmp.__key__),) );

  def test_08_str( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    self.assertEqual( str( home.tmp ),
                      'Object(%s)' % (repr(home.tmp.__key__),) );

  def test_09_attribute_error( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    self.assertRaises( AttributeError, eval, 'home.tmp.a', 
                       globals(), locals() );


#  python 2.6 (not in 2.5)
#  def test_format( self ):
#    # very minimal test of functionality
#    home = eval( 'self.storage.' + storserv_config.USERS_OBJECT + \
#                 '[%s]' % (repr('root'),) );
#    home.tmp = pstorage.Object( self.storage );
#
#    
#    self.assertRaises( ValueError, "invalid format string!!!".format, 
#                       home.tmp );
#
#    self.assertEqual( "".format( home.tmp ), 
#                      str( home.tmp.fastlist1 ) );


#  def test_copy( self ):
#    # objects in python 2.6 don't have a default copy command so we don't 
#    # support them here by default either
#    home = eval( 'self.storage.' + storserv_config.USERS_OBJECT + \
#                 '[%s]' % (repr('root'),) );
#    home.tmp = pstorage.Object( self.storage );
#
#    home.tmp.a = pstorage.Object( self.storage );
#    
#    self.assertRaises( AttributeError, eval, 'home.tmp.a.copy', globals(), locals() );

################################################################################

class Test08None( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_none( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = None;
    home.tmp.test2 = None;

    self.assertEqual( home.tmp.test1, home.tmp.test2 );
    self.assertEqual( home.tmp.test1, None );
    self.assertEqual( type(home.tmp.test1), type(None) );

    self.assertEqual( bool(home.tmp.test1), False );

################################################################################

class Test09Boolean( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_boolean( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = True;
    home.tmp.test2 = False;
    home.tmp.test3 = True;

    self.assertEqual( type( home.tmp.test1 ), type( False ) );
    self.assertEqual( type( home.tmp.test2 ), type( True ) );
    self.assertEqual( home.tmp.test1 and home.tmp.test2, False );
    self.assertEqual( home.tmp.test1 or home.tmp.test2, True );

    self.assertEqual( home.tmp.test1, home.tmp.test3 );
    self.assertEqual( home.tmp.test1, True );
    self.assertEqual( home.tmp.test2, False );

    self.assertEqual( int(home.tmp.test1), 1 );
    self.assertEqual( int(home.tmp.test2), 0 );

################################################################################

class Test10Integer( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_int( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = 1;
    home.tmp.test2 = 2;
    home.tmp.test4 = 2;

    self.assertEqual( type( home.tmp.test1 ), type( 0 ) );
    self.assertEqual( type( home.tmp.test2 ), type( 0 ) );
    home.tmp.test3 = home.tmp.test1 + home.tmp.test2;
    self.assertEqual( home.tmp.test3, 3 );

    self.assertEqual( home.tmp.test2, home.tmp.test4 );
    self.assertEqual( home.tmp.test1, 1 );    
    self.assertEqual( home.tmp.test2, 2 );    

    # check if this version of python's max int matches the max-int built
    # into postgresql (2147483647 or 9223372036854775807)
    self.assertTrue( sys.maxsize in [2147483647,9223372036854775807] );

    # python 2.6
    #self.assertEqual( home.tmp.test1.numerator, 1 );
    #self.assertEqual( home.tmp.test1.denominator, 1 );
    #self.assertEqual( home.tmp.test1.real, 1 );
    #self.assertEqual( home.tmp.test1.imag, 0 );
    #self.assertEqual( home.tmp.test1.conjugate(), 1 );

################################################################################

class Test11LongInteger( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_long( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = 1;
    home.tmp.test2 = 2;
    home.tmp.test4 = 2;

    self.assertEqual( type( home.tmp.test1 ), type( 0 ) );
    self.assertEqual( type( home.tmp.test2 ), type( 0 ) );
    home.tmp.test3 = home.tmp.test1 + home.tmp.test2;
    self.assertEqual( home.tmp.test3, 3 );

    self.assertEqual( home.tmp.test2, home.tmp.test4 );
    self.assertEqual( home.tmp.test1, 1 );    
    self.assertEqual( home.tmp.test2, 2 );    

################################################################################

class Test12Float( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_long( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = 1.5;
    home.tmp.test2 = 2.5;
    home.tmp.test4 = 2.5;

    self.assertEqual( type( home.tmp.test1 ), type( 0.0 ) );
    self.assertEqual( type( home.tmp.test2 ), type( 0.0 ) );
    home.tmp.test3 = home.tmp.test1 + home.tmp.test2;
    self.assertEqual( home.tmp.test3, 4.0 );

    self.assertEqual( home.tmp.test2, home.tmp.test4 );
    self.assertEqual( home.tmp.test1, 1.5 );
    self.assertEqual( home.tmp.test2, 2.5 );

    # python 2.6
    #self.assertEqual( home.tmp.test1.as_integer_ratio(), 
    #                  (1.1).as_integer_ratio() );

    # python 2.6
    #self.assertEqual( home.tmp.test1.is_integer(), False );

    # python 2.6
    #self.assertEqual( type( home.tmp.test1.hex() ), type("") );

    # fromhex() ???

################################################################################

class Test13String( unittest.TestCase ):
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_string( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = 'hello';
    home.tmp.test2 = 'world';
    home.tmp.test4 = 'world';

    self.assertEqual( home.tmp.test1[1], 'e' );
    self.assertEqual( home.tmp.test2[1], 'o' );

    self.assertEqual( home.tmp.test1[1:4], 'ell' );
    self.assertEqual( home.tmp.test2[1:4], 'orl' );
    self.assertEqual( home.tmp.test1[1:4:2], 'el' );
    self.assertEqual( home.tmp.test2[1:4:2], 'ol' );

    self.assertEqual( len(home.tmp.test1), 5 );
    self.assertEqual( len(home.tmp.test2), 5 );
    self.assertEqual( min(home.tmp.test1), 'e' );
    self.assertEqual( min(home.tmp.test2), 'd' );
    self.assertEqual( max(home.tmp.test1), 'o' );
    self.assertEqual( max(home.tmp.test2), 'w' );

    # all(), any() ?

    # The string methods in Table 3.5 of Python Essentail Object, 4th Ed.,
    # are not included here because home.tmp.test1 returns a python string 
    # (not a SnakeCharmer string) and so any (non-sideffecting)  operations 
    # which operate on these are guaranteed to work.
    self.assertEqual( type( home.tmp.test1 ), type( '' ) );
    self.assertEqual( type( home.tmp.test2 ), type( '' ) );
    home.tmp.test3 = home.tmp.test1 + ' ' + home.tmp.test2;
    self.assertEqual( home.tmp.test3, 'hello world' );

    self.assertEqual( home.tmp.test2, home.tmp.test4 );
    self.assertEqual( home.tmp.test1, 'hello' );    
    self.assertEqual( home.tmp.test2, 'world' );    

################################################################################

class Test14Method( unittest.TestCase ):

  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_method( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.hello_world = self.storage.Method();


    home.tmp.hello_world.method_text="""\
def hello_world( self ):
  return "Hello, world!";
"""; 

    home.tmp.hello_world.compile();

    self.assertEqual( home.tmp.hello_world(), "Hello, world!" );

  def test_not_method( self ):

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.hello_world = self.storage.Method();

    home.tmp.hello_world.method_text="Hello, world!";

    self.assertRaises( SyntaxError, home.tmp.hello_world.compile );

  def test_syntax_error( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.hello_world = self.storage.Method()
    home.tmp.hello_world.method_text="""\
def hello_world( self ):
  print "ok";
  in for if break def class;
""";

    home.tmp.hello_world.compile();
    self.assertRaises( SyntaxError, home.tmp.hello_world );

################################################################################

class Test15List( unittest.TestCase ):

  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_01_fastlist( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.fastlist = [66.25, 333, 334, 1, 1234.5];
    self.assertEqual( home.tmp.fastlist[0], 66.25 );
    self.assertEqual( home.tmp.fastlist[1], 333 );
    self.assertEqual( home.tmp.fastlist[2], 334 );
    self.assertEqual( home.tmp.fastlist[3], 1 );
    self.assertEqual( home.tmp.fastlist[4], 1234.5 );
    self.assertEqual( home.tmp.fastlist[-1], 1234.5 );
    self.assertEqual( home.tmp.fastlist[-2], 1 );
    self.assertEqual( type(home.tmp.fastlist[0]), type(66.25) );
    self.assertEqual( type(home.tmp.fastlist[1]), type(333) );
    self.assertEqual( type(home.tmp.fastlist[2]), type(334) );
    self.assertEqual( type(home.tmp.fastlist[3]), type(1) );
    self.assertEqual( type(home.tmp.fastlist[4]), type(1234.5) );

    self.assertEqual( home.tmp.fastlist[1:4], [333, 334, 1] );
    self.assertEqual( home.tmp.fastlist[1:4:2], [333, 1] );


    self.assertEqual( len(home.tmp.fastlist), 5 );
    self.assertEqual( min(home.tmp.fastlist), 1 );
    self.assertEqual( max(home.tmp.fastlist), 1234.5 );
    self.assertEqual( sum(home.tmp.fastlist), 1968.75 );

    self.assertRaises( IndexError, home.tmp.fastlist.__setitem__, 100, 4 );



    # all(), any()

  def test_02_append( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.list = self.storage.List();
    home.tmp.list.append( 'a' );
    home.tmp.list.append( 'b' );
    home.tmp.list.append( 'c' );
    home.tmp.list.append( 'd' );

    self.assertEqual( home.tmp.list[0], 'a' );
    self.assertEqual( home.tmp.list[1], 'b' );
    self.assertEqual( home.tmp.list[2], 'c' );
    self.assertEqual( home.tmp.list[3], 'd' );

    self.assertEqual( len( home.tmp.list.getcontents()), 4 );

  def test_03_slice_and_len( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist = list(range( 0, 10));
    self.assertEqual( home.tmp.fastlist[3:6], [3,4,5] );
    self.assertEqual( home.tmp.fastlist[1:9:2], [1,3,5,7] );
    self.assertEqual( len(home.tmp.fastlist), 10 );

  def test_04_replace( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist = list(range( 0, 10));
    home.tmp.fastlist[3] = 100;
    self.assertEqual( home.tmp.fastlist[:], [0,1,2,100,4,5,6,7,8,9] );

  def test_05_del( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist = list(range( 0, 10));
    del home.tmp.fastlist[3];
    self.assertEqual( home.tmp.fastlist[:], [0,1,2,4,5,6,7,8,9] );
     
  def test_06_extend( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range( 0, 10));
    home.tmp.fastlist2 = list(range( 10, 20));

    home.tmp.fastlist1.extend( home.tmp.fastlist2 );
    self.assertEqual( home.tmp.fastlist1[:], list(range(0,20)) );

  def test_07_count( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist = [1,2,2,3,3,3,4,4,4,4,3,3,3,2,2,1];
    self.assertEqual( home.tmp.fastlist.count( 1 ), 2 );
    self.assertEqual( home.tmp.fastlist.count( 2 ), 4 );
    self.assertEqual( home.tmp.fastlist.count( 3 ), 6 );
    self.assertEqual( home.tmp.fastlist.count( 4 ), 4 );

  def test_08_index( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist = list(range( 0, 100));
    home.tmp.fastlist[7] = 7;
    home.tmp.fastlist[14] = 7;
    home.tmp.fastlist[21] = 7;

    self.assertEqual( home.tmp.fastlist.index( 7 ), 7 );
    self.assertEqual( home.tmp.fastlist.index( 7, 8 ), 14 );
    self.assertRaises( ValueError, home.tmp.fastlist.index, 7, 8, 13 );

  def test_09_insert( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range( 0, 100));
    home.tmp.fastlist1.insert(50,'fifty');
    self.assertEqual( home.tmp.fastlist1[50], 'fifty' );
    self.assertEqual( home.tmp.fastlist1[:50], list(range(0,50)) );
    self.assertEqual( home.tmp.fastlist1[51:], list(range(50,100)) );

  def test_10_pop( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range( 0, 100));

    val = home.tmp.fastlist1.pop();
    self.assertEqual( home.tmp.fastlist1, list(range(0,99)) );
    self.assertEqual( val, 99 );

    val = home.tmp.fastlist1.pop(50);
    self.assertEqual( home.tmp.fastlist1, list(range(0,50))+list(range(51,99)) );
    self.assertEqual( val, 50 );
    
  def test_11_remove( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = 5*list(range(0,5));

    home.tmp.fastlist1.remove(3);

    self.assertEqual( [0,1,2,4]+4*[0,1,2,3,4], home.tmp.fastlist1 );

    self.assertRaises( ValueError, home.tmp.fastlist1.remove, 700 );

  def test_12_reverse( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.fastlist1 = list(range(0,25));
    home.tmp.fastlist1.reverse();
    self.assertEqual( home.tmp.fastlist1, list(range(24,-1,-1)) );

    home.tmp.fastlist1 = list(range(0,24));
    home.tmp.fastlist1.reverse();
    self.assertEqual( home.tmp.fastlist1, list(range(23,-1,-1)) );

  def test_13_sort( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,25));
    home.tmp.fastlist2 = list(range(24,-1,-1));
    home.tmp.fastlist3 = [6, 24, 0, 16, 19, 4, 18, 1, 12, 2, 22, 15, 14, 23, 7, 17, 5, 3, 13, 20, 11, 9, 8, 21, 10];

    home.tmp.fastlist1.sort();
    home.tmp.fastlist2.sort();
    home.tmp.fastlist3.sort();

    self.assertEqual( home.tmp.fastlist1, list(range(0,25)) );
    self.assertEqual( home.tmp.fastlist2, list(range(0,25)) );
    self.assertEqual( home.tmp.fastlist3, list(range(0,25)) );

  def test_14_equality( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));

    self.assertEqual( home.tmp.fastlist1, home.tmp.fastlist2 );
    self.assertEqual( home.tmp.fastlist1, list(range(0,5)) );

  def test_15_lt( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));
    home.tmp.fastlist3 = list(range(0,4));
    home.tmp.fastlist4 = [0,1,3,3,4];
    home.tmp.fastlist5 = [0,1,1,3,4];

    self.assertEqual( home.tmp.fastlist1 < home.tmp.fastlist2, False );
    self.assertEqual( home.tmp.fastlist1 < home.tmp.fastlist3, False );
    self.assertEqual( home.tmp.fastlist1 < home.tmp.fastlist4, True );
    self.assertEqual( home.tmp.fastlist1 < home.tmp.fastlist5, False );

  def test_16_le( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));
    home.tmp.fastlist3 = list(range(0,4));
    home.tmp.fastlist4 = [0,1,3,3,4];
    home.tmp.fastlist5 = [0,1,1,3,4];

    self.assertEqual( home.tmp.fastlist1 <= home.tmp.fastlist2, True );
    self.assertEqual( home.tmp.fastlist1 <= home.tmp.fastlist3, False );
    self.assertEqual( home.tmp.fastlist1 <= home.tmp.fastlist4, True );
    self.assertEqual( home.tmp.fastlist1 <= home.tmp.fastlist5, False );

  def test_17_gt( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));
    home.tmp.fastlist3 = list(range(0,4));
    home.tmp.fastlist4 = [0,1,3,3,4];
    home.tmp.fastlist5 = [0,1,1,3,4];

    self.assertEqual( home.tmp.fastlist1 > home.tmp.fastlist2, False );
    self.assertEqual( home.tmp.fastlist1 > home.tmp.fastlist3, True);
    self.assertEqual( home.tmp.fastlist1 > home.tmp.fastlist4, False );
    self.assertEqual( home.tmp.fastlist1 > home.tmp.fastlist5, True );

  def test_18_ge( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));
    home.tmp.fastlist3 = list(range(0,4));
    home.tmp.fastlist4 = [0,1,3,3,4];
    home.tmp.fastlist5 = [0,1,1,3,4];

    self.assertEqual( home.tmp.fastlist1 >= home.tmp.fastlist2, True );
    self.assertEqual( home.tmp.fastlist1 >= home.tmp.fastlist3, True );
    self.assertEqual( home.tmp.fastlist1 >= home.tmp.fastlist4, False );
    self.assertEqual( home.tmp.fastlist1 >= home.tmp.fastlist5, True );

  def test_19_ne( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    home.tmp.fastlist2 = list(range(0,5));
    home.tmp.fastlist3 = list(range(0,4));
    home.tmp.fastlist4 = [0,1,3,3,4];
    home.tmp.fastlist5 = [0,1,1,3,4];

    self.assertEqual( home.tmp.fastlist1 != home.tmp.fastlist2, False );
    self.assertEqual( home.tmp.fastlist1 != home.tmp.fastlist3, True );
    self.assertEqual( home.tmp.fastlist1 != home.tmp.fastlist4, True );
    self.assertEqual( home.tmp.fastlist1 != home.tmp.fastlist5, True );

  def test_20_iter( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    items = [];
    for i in home.tmp.fastlist1:
      items.append( i );
    self.assertEqual( items, list(range(0,5)) );
      

  def test_21_bool( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = [0];
    home.tmp.fastlist2 = [None];
    home.tmp.fastlist3 = [];
    home.tmp.fastlist4 = [[]];

    self.assertEqual( bool(home.tmp.fastlist1), True );
    self.assertEqual( bool(home.tmp.fastlist2), True );
    self.assertEqual( bool(home.tmp.fastlist3), False );
    self.assertEqual( bool(home.tmp.fastlist4), True );

  
  def test_22_contains( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
    self.assertEqual( 3 in home.tmp.fastlist1, True )
    self.assertEqual( 5 in home.tmp.fastlist1, False )

#  python 2.6 (not in 2.5)
#  def test_format( self ):
#    home = eval( 'self.storage.' + storserv_config.USERS_OBJECT + \
#                 '[%s]' % (repr('root'),) );
#    home.tmp = pstorage.Object( self.storage );
#    home.tmp.fastlist1 = range(0,5);
#    
#    self.assertRaises( ValueError, format, home.tmp.fastlist1, 
#                       "invalid format string!!!" );
#
#    self.assertEqual( format( home.tmp.fastlist1, "" ), 
#                      str( home.tmp.fastlist1 ) );


  def test_23_repr( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
   
    self.assertEqual( repr( home.tmp.fastlist1 ),
                      'List(%s)' % (repr(home.tmp.fastlist1.__key__),) );
 
  def test_24_str( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));
   
    self.assertEqual( repr( home.tmp.fastlist1 ),
                      'List(%s)' % (repr(home.tmp.fastlist1.__key__),) );
 

#  def test_copy( self ):
#    # lists in python 2.6 don't have a default copy command so we don't 
#    # support them here by default either
#    home = eval( 'self.storage.' + storserv_config.USERS_OBJECT + \
#                 '[%s]' % (repr('root'),) );
#    home.tmp = pstorage.Object( self.storage );
#
#    home.tmp.a = [];
#    
#    self.assertRaises( AttributeError, home.tmp.a.copy );

  def test_25_index_error( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.fastlist1 = list(range(0,5));

    self.assertRaises( IndexError, eval, "home.tmp.fastlist1[7]", globals(), locals() );


################################################################################

class Test16Dict( unittest.TestCase ):

  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_01_construct( self ):
    # also tests: len, getitem, setitem
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = self.storage.Dict();
    home.tmp.tel['guido'] = 4127;
    home.tmp.tel['jack'] = 4098;
    home.tmp.tel['irv'] = 4127;

    self.assertEqual( home.tmp.tel['guido'], 4127 );
    self.assertEqual( home.tmp.tel['jack'], 4098 );
    self.assertEqual( home.tmp.tel['irv'], 4127 );

    self.assertEqual( len(home.tmp.tel), 3 );

  def test_01b_key_error( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = self.storage.Dict();

    self.assertRaises( KeyError, eval, "home.tmp.tel['frog']", globals(), locals() );

  def test_02_resetting( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = self.storage.Dict();
    home.tmp.tel['guido'] = 1234;
    home.tmp.tel['guido'] = 5678;
    home.tmp.tel['guido'] = 9012;

    self.assertEqual( len(home.tmp.tel), 1 );

  def test_03_del( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = self.storage.Dict();
    home.tmp.tel['aa'] = 'eh?';
    home.tmp.tel['bb'] = 'bee';  

    self.assertEqual( len(home.tmp.tel), 2 );
    del home.tmp.tel['bb'];
    self.assertEqual( len(home.tmp.tel), 1 );

  def test_04_fastdict( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = { 'guido': 4127, 'jack': 4098, 'irv': 4128 };

    self.assertEqual( home.tmp.tel['guido'], 4127 );    
    self.assertEqual( home.tmp.tel['jack'], 4098 );
    self.assertEqual( home.tmp.tel['irv'], 4128 );

    self.assertEqual( len(home.tmp.tel), 3 );

  def test_05_types( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.dict = { 'string': 'hello', 'int': 4098, 'float': 41.28 };

    self.assertEqual( type(home.tmp.dict['string']), type('') );
    self.assertEqual( type(home.tmp.dict['int']), type(0) );
    self.assertEqual( type(home.tmp.dict['float']), type(0.1) );

  def test_06_contains( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.dict = { 'a': 'A', 'b': 'B', 'c': 'C' };

    self.assertTrue( 'a' in home.tmp.dict );
    self.assertTrue( 'b' in home.tmp.dict );
    self.assertTrue( 'c' in home.tmp.dict );
    self.assertFalse( 'A' in home.tmp.dict );
    self.assertFalse( 'B' in home.tmp.dict );
    self.assertFalse( 'C' in home.tmp.dict );

  def test_07_comparisons( self ):
    # In Python 2.6 and eariler, dictionary comparisons operate as though
    # comparing stored key/value lists.
    #
    # In Python 3.0 dictonary comparisons other than equality tests generate
    # an error:
    # TypeError: unorderable types:  dict() < dict()

    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();


    home.tmp.dicta = { 'a': 'A' };
    home.tmp.dictb = { 'a': 'A', 'b': 'B' };
    home.tmp.dictc1 = { 'a': 'A', 'b': 'B', 'c': 'C' };
    home.tmp.dictc2 = { 'a': 'A', 'c': 'C', 'b': 'B' };
    home.tmp.dictc3 = { 'a': 'A', 'b': 'B', 'c': 'D' };
    home.tmp.abcd = {'a': 'b', 'c': 'd' };
    home.tmp.abdc = {'a': 'b', 'd': 'c' };
    home.tmp.acbd = {'a': 'c', 'b': 'd' };
    home.tmp.acdb = {'a': 'c', 'd': 'b' };
    home.tmp.adbc = {'a': 'd', 'b': 'c' };
    home.tmp.adcb = {'a': 'd', 'c': 'b' };
    home.tmp.bacd = {'b': 'a', 'c': 'd' };
    home.tmp.badc = {'b': 'a', 'd': 'c' };
    home.tmp.bcad = {'b': 'c', 'a': 'd' };
    home.tmp.bcda = {'b': 'c', 'd': 'a' };
    home.tmp.bdac = {'b': 'd', 'a': 'c' };
    home.tmp.bdca = {'b': 'd', 'c': 'a' };
    home.tmp.cabd = {'c': 'a', 'b': 'd' };
    home.tmp.cadb = {'c': 'a', 'd': 'b' };
    home.tmp.cbad = {'c': 'b', 'a': 'd' };
    home.tmp.cbda = {'c': 'b', 'd': 'a' };
    home.tmp.cdab = {'c': 'd', 'a': 'b' };
    home.tmp.cdba = {'c': 'd', 'b': 'a' };
    home.tmp.dabc = {'d': 'a', 'b': 'c' };
    home.tmp.dacb = {'d': 'a', 'c': 'b' };
    home.tmp.dbac = {'d': 'b', 'a': 'c' };
    home.tmp.dbca = {'d': 'b', 'c': 'a' };
    home.tmp.dcab = {'d': 'c', 'a': 'b' };
    home.tmp.dcba = {'d': 'c', 'b': 'a' };

    self.assertFalse( home.tmp.dicta == home.tmp.dictb );
    self.assertFalse( home.tmp.dictb == home.tmp.dictc1 );
    self.assertEqual( home.tmp.dictc1, home.tmp.dictc2 );
    self.assertTrue( home.tmp.dictc1==home.tmp.dictc2 );
    self.assertTrue( home.tmp.dictc1=={ 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertFalse( home.tmp.dictc2 == home.tmp.dictc3 );

    self.assertTrue( home.tmp.dicta != home.tmp.dictb );
    self.assertTrue( home.tmp.dictb != home.tmp.dictc1 );
    self.assertFalse( home.tmp.dictc1!=home.tmp.dictc2 );
    self.assertFalse( home.tmp.dictc1!={ 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertTrue( home.tmp.dictc2 != home.tmp.dictc3 );


    self.assertTrue( home.tmp.dicta < home.tmp.dictb );
    self.assertTrue( home.tmp.dictb < home.tmp.dictc1 );
    self.assertFalse( home.tmp.dictc1 < home.tmp.dictc2 );
    self.assertFalse( home.tmp.dictc1 < { 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertTrue( home.tmp.dictc2 < home.tmp.dictc3 );

#    self.assertTrue( home.tmp.abcd < 
#                     home.tmp.abdc <
#                     home.tmp.acbd <
#                     home.tmp.acdb <
#                     home.tmp.adbc <
#                     home.tmp.adcb <
#                     home.tmp.bacd <
#                     home.tmp.badc <
#                     home.tmp.bcad <
#                     home.tmp.bcda <
#                     home.tmp.bdac <
#                     home.tmp.bdca <
#                     home.tmp.cabd <
#                     home.tmp.cadb <
#                     home.tmp.cbad <
#                     home.tmp.cbda <
#                     home.tmp.cdab <
#                     home.tmp.cdba <
#                     home.tmp.dabc <
#                     home.tmp.dacb <
#                     home.tmp.dbac <
#                     home.tmp.dbca <
#                     home.tmp.dcab <
#                     home.tmp.dcba );

    self.assertFalse( home.tmp.dicta > home.tmp.dictb );
    self.assertFalse( home.tmp.dictb > home.tmp.dictc1 );
    self.assertFalse( home.tmp.dictc1 > home.tmp.dictc2 );
    self.assertFalse( home.tmp.dictc1 > { 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertTrue( home.tmp.dictc2 < home.tmp.dictc3 );
   
#    self.assertTrue( home.tmp.dcba >
#                     home.tmp.dcab >
#                     home.tmp.dbca >
#                     home.tmp.dbac >
#                     home.tmp.dacb >
#                     home.tmp.dabc >
#                     home.tmp.cdba >
#                     home.tmp.cdab >
#                     home.tmp.cbda >
#                     home.tmp.cbad >
#                     home.tmp.cadb >
#                     home.tmp.cabd >
#                     home.tmp.bdca >
#                     home.tmp.bdac >
#                     home.tmp.bcda >
#                     home.tmp.bcad >
#                     home.tmp.badc >
#                     home.tmp.bacd >
#                     home.tmp.adcb >
#                     home.tmp.adbc >
#                     home.tmp.acdb >
#                     home.tmp.acbd >
#                     home.tmp.abdc >
#                     home.tmp.abcd );


    self.assertTrue( home.tmp.dicta <= home.tmp.dictb );
    self.assertTrue( home.tmp.dictb <= home.tmp.dictc1 );
    self.assertTrue( home.tmp.dictc1 <= home.tmp.dictc2 );
    self.assertTrue( home.tmp.dictc1 <= { 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertFalse( home.tmp.dictc2 >= home.tmp.dictc3 );
  
    self.assertFalse( home.tmp.dicta >= home.tmp.dictb );
    self.assertFalse( home.tmp.dictb >= home.tmp.dictc1 );
    self.assertTrue( home.tmp.dictc1 >= home.tmp.dictc2 );
    self.assertTrue( home.tmp.dictc1 >= { 'a': 'A', 'b': 'B', 'c': 'C' } );
    self.assertTrue( home.tmp.dictc2 <= home.tmp.dictc3 );
  
  def test_08_clear( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.tel = self.storage.Dict();
    home.tmp.tel['aa'] = 'eh?';
    home.tmp.tel['bb'] = 'bee';  

    self.assertEqual( len(home.tmp.tel), 2 );
    home.tmp.tel.clear();
    self.assertEqual( len(home.tmp.tel), 0 );

   
  def test_09_get( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    self.assertEquals( home.tmp.test.get( 'a' ), 1 );
    self.assertEquals( home.tmp.test.get( 'd', 7 ), 7 );
    self.assertEquals( home.tmp.test.get( 'd' ), None );

  def test_10_has_key( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };
    self.assertTrue( 'a' in home.tmp.test );
    self.assertTrue( 'b' in home.tmp.test );
    self.assertTrue( 'c' in home.tmp.test );
    self.assertFalse( 'd' in home.tmp.test );

  def test_11_items( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };
    self.assertTrue( sorted( home.tmp.test.items() ), 
                     sorted( { 'a': 1, 'b': 2, 'c': 3 }.items() ) );
    self.assertTrue( type( list(home.tmp.test.items()) ), 
                     type( list({ 'a': 1, 'b': 2, 'c': 3 }.items()) ) );

  def test_12_keys( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    self.assertTrue( sorted( home.tmp.test.keys() ),
                     sorted( { 'a': 1, 'b': 2, 'c': 3 }.keys() ) );
    self.assertTrue( type( list(home.tmp.test.keys()) ), 
                     type( list({ 'a': 1, 'b': 2, 'c': 3 }.keys()) ) );

  def test_13_pop( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();


    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    value = home.tmp.test.pop( 'b' );

    self.assertTrue( home.tmp.test == { 'a':1, 'c':3 } );
    self.assertEqual( value, ('b',2) );

  def test_14_popitem( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    item1 = home.tmp.test.popitem();
    item2 = home.tmp.test.popitem();
    item3 = home.tmp.test.popitem();

    new_dict = dict( [ item1, item2, item3 ] );

    self.assertEqual( len( home.tmp.test ), 0 );
    self.assertEqual( new_dict, {'a': 1, 'b': 2, 'c': 3 } );


  def test_15_update( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    home.tmp.test.update( { 'c': 4, 'd': 5 } );

    self.assertEqual( home.tmp.test, { 'a': 1, 'b': 2, 'c': 4, 'd': 5 } );

    home.tmp.test.update( e=6, f=7 );

    self.assertEqual( home.tmp.test, { 'a': 1, 'b': 2, 'c': 4, 'd': 5, 'e': 6, 
                                       'f': 7 } );

  def test_16_values( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': 3 };

    self.assertEqual( sorted( home.tmp.test.values() ), [1,2,3] );


  def test_17_dictionary_of_lists( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': [3,4] };

    self.assertEqual( home.tmp.test['c'], [3,4] );


  def test_18_dictionary_of_dictionary( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test = { 'a': 1, 'b': 2, 'c': {'3':4} };

    self.assertEqual( home.tmp.test['c']['3'], 4 );



#  python 2.6 (not in 2.5)
#  def test_format( self ):
#    raise Exception, 'not implemented';

  def test_19_repr( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.test = self.storage.Dict();

    self.assertEqual( repr( home.tmp.test ),
                      'Dict(%s)' % (repr(home.tmp.test.__key__),) );

  def test_20_str( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();
    home.tmp.test = self.storage.Dict();

    self.assertEqual( str( home.tmp.test ),
                      'Dict(%s)' % (repr(home.tmp.test.__key__),) );





################################################################################

class Test17Link( unittest.TestCase ):
  """
  """
  def setUp( self ):
    self.storage = pstorage.Storage( '127.0.0.1' );
    self.storage.login( 'root', password );

  def test_01_construct( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp.test1 = self.storage.Object();
    home.tmp.test1.test2 = self.storage.Object();

    home.tmp.link1 = home.tmp.test1;

    self.assertEqual( [os.path.basename(item) for item in \
                               home.tmp.test1.getcontents()], ['test2'] );
    self.assertEqual( [os.path.basename(item) for item in \
                               home.tmp.link1.getcontents()], ['test2'] );

    del home.tmp.link1;

    self.assertEqual( [os.path.basename(item) for item in \
                               home.tmp.test1.getcontents()], ['test2'] );

  def test_02_del_linkedto( self ):
    home = self.storage.Server.Users['root'];
    home.tmp = self.storage.Object();

    home.tmp = self.storage.Object();

    home.tmp.test1 = self.storage.Object();
    home.tmp.test1.test2 = self.storage.Object();

    home.tmp.link1 = home.tmp.test1;

    del home.tmp.test1;

    # check that the link is not gone too
    self.assertEqual( [os.path.basename(item) for item in \
                               home.tmp.getcontents()], ['link1'] );


################################################################################

if __name__ == '__main__':

  if len(sys.argv)>1:
    items = [ eval(item) for item in sys.argv[1:] ];
  else:
    items = [
      Test01Connection,
      Test02BadPasswordLogin,
      Test03GoodPasswordLogin,
      Test04BadUserLogin,
      Test05Logout,
      Test06BadAccess,
      Test07Object,
      Test08None,
      Test09Boolean,
      Test10Integer,
      Test11LongInteger,
      Test12Float,
      Test13String,
      Test14Method,
      Test15List,
      Test16Dict,
      Test17Link,
      ];

  password = getpass.getpass( "Enter root password: " );

  suite = unittest.TestSuite()
  for test in items:
    suite.addTest( unittest.makeSuite(test) );
  unittest.TextTestRunner(verbosity=2).run(suite);


