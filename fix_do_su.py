import pstorage;
import getpass;

password = getpass.getpass( "Enter root password: " );


storage = pstorage.Storage( '127.0.0.1' );
storage.login( 'root', password );

storage.Library.STOSH.do_compile.compile();
storage.Library.STOSH.do_edit.compile();
storage.Library.STOSH.do_ls.compile();
storage.Library.STOSH.do_make.compile();
storage.Library.STOSH.do_rm.compile();
storage.Library.STOSH.do_su.compile();
storage.Library.STOSH.do_test.compile();


