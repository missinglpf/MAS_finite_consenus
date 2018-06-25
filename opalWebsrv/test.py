#! /usr/bin/python
import struct
import socket
import urllib
import subprocess
import sys
import time
import os
import traceback
def portIsOpened(hostip, port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect_ex((hostip,port))
	if result == 0:
		return True
	else:
		return False

def fakeOpalCom(vals, the_format_in, the_format_out, hostip, port):
	sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	d4= struct.pack(the_format_out, *vals)
	sent=sock.sendto(d4, (hostip, port))
	print "Opal sends", vals
	rawdata,server=sock.recvfrom(4096)
	sock.close()
	data = struct.unpack(the_format_in, rawdata)
	print "Opal recvd", data
	return data

def testsrv(http_port, opal_port, nbIn, nbOut):
	print "Testing with a new set"
	assert(not(portIsOpened('127.0.0.1',http_port)))
	assert(not(portIsOpened('127.0.0.1',opal_port)))
	p = subprocess.Popen([os.getcwd()+ "/opalWebSrv.py", "-s", "-I", str(nbIn), "-O", str(nbOut)], bufsize=1024, stdin=sys.stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	try:
		time.sleep(0.5)
		the_format_in='<hih'+str(nbIn)+'d'
		the_format_out='<hih'+str(nbOut)+'d'
		HTTP_PORT=str(8000)
		UDP_IP='127.0.0.1'
		UDP_PORT=50000

		vals=[1,2,3]+range(1,nbOut+1)
		opalret = fakeOpalCom(vals, the_format_in, the_format_out, UDP_IP, UDP_PORT)
		assert(opalret==tuple([1,0,8*nbIn]+[0 for i in range(nbIn)]))

		f=urllib.urlopen('http://localhost:'+HTTP_PORT+'/asyncsrv/set?valin0=12.5&valin1=40.2')
		print f.read()
		f=urllib.urlopen('http://localhost:'+HTTP_PORT+'/asyncsrv/get?name0=valout0&name1=valout1')
		ret=f.read()
		print ret
		assert(ret=='{"valout0": 1.0, "valout1": 2.0}')

		vals=[1,2,3,10.]+range(2,nbOut+1)
		opalret = fakeOpalCom(vals, the_format_in, the_format_out, UDP_IP, UDP_PORT)
		assert(opalret==tuple([1,1,8*nbIn]+[12.5,40.2]+ [0 for i in range(nbIn-2)]))
		f=urllib.urlopen('http://localhost:'+HTTP_PORT+'/asyncsrv/get?name0=valout0&name1=valout1')
		assert(f.read()=='{"valout0": 10.0, "valout1": 2.0}')
	except Exception as error:
		p.kill()
		traceback.print_exc()
		raise(error)
	p.kill()
params_list = [
	{"http_port": 8000, "opal_port": 50000,"nbIn":16, "nbOut":16},
	{"http_port": 8001, "opal_port": 50001,"nbIn":10, "nbOut":12}
	]
for params in params_list:
	testsrv(**params)
print "Testing succeeded"
