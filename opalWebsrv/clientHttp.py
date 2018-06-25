#! /usr/bin/python
import sys
import urllib
hostname='localhost'
port='8000'
argc=len(sys.argv)
if argc>=2:
	hostname=sys.argv[1]
if argc>=3:
	port=sys.argv[2]

f=urllib.urlopen('http://'+hostname+':'+port+'/asyncsrv/set?valin0=1&valin1=1.44')
print f.read()
f=urllib.urlopen('http://'+hostname+':'+port+'/asyncsrv/get?name0=valout0&name1=valout1')
print f.read()
