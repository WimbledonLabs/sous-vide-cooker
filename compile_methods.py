import pstorage
import os
import getpass


password = getpass.getpass( "Enter root password: " );

storage = pstorage.Storage( '127.0.0.1' );
storage.login( 'root', password );

for dirpath,dirnames,filenames in os.walk("storserv_data"):
	print(dirpath);
	if "marshalled_code_object" in filenames:
		#Method found and needs to be compiled
		method = dirpath.replace('/','.');
		method = method.replace('storserv_data','storage');
		method = method+".compile()";
		print("executing:\t" + method + '\n');
		exec(method);
