#! /usr/bin/python
#    Http server for data exchange with opal rt simulation
#    Copyright (C) 2015  Cedric Boudinet <cedric.boudinet@g2elab.grenoble-inp.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import SocketServer
import threading
import struct
import time
import BaseHTTPServer
import urlparse
import optparse
import sys
version = "1.3"
running = True
verbose_http_handler = True
UDP_send_host = "192.168.127.101"
UDP_send_port = 65000

class MyHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def __init__(self, request, client_address, server):
		BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)
	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/xml")
		self.end_headers()

	def do_GET(self):
		self.__urlToFunDic ={
		'/asyncsrv/set' : self.set_values,
		'/asyncsrv/get' : self.get_values,
		}
		parsedReq=urlparse.urlparse(self.path)
		#python2.4 on Opal :-((, urlparse returns a tuple
		path=parsedReq[2]
		args=parsedReq[4]
		if path in self.__urlToFunDic:
			ret=self.__urlToFunDic[path](self.splitArgs(args))
		else:
			ret = { "status" : "Page not found"}
		ret = repr(ret).replace("'",'"')
		self.send_response(200)
		self.send_header( "Content-type", "application/json")
		self.end_headers()
		self.wfile.write(str(ret))
		return

	def splitArgs(self, args):
		return [arg.split('=') for arg in args.split('&')]

	def set_values(self, set_req):
		#print "set_values calling with args:", set_req
		dataHandler.set_invalues(set_req)
		return { "status" : "Ok" }

	def get_values(self, get_req):
		#print "get_values calling with args:", get_req
		return dataHandler.get_outvalues(get_req)

	def log_message(self, format, *args):
		if verbose_http_handler:
			BaseHTTPServer.BaseHTTPRequestHandler.log_message(self, format, *args)
		else:
			return
def activateHttpLogging(status):
	global verbose_http_handler
	if status in ['on', 1, True]:
		verbose_http_handler=True
	else:
		verbose_http_handler=False
class MyDataHandler(object):
	def __init__(self, size_in, size_out, default_value):
		#OpalRT sets output values and reads input values
		#The web clients read output values and set input values
		self._invalues=[default_value for i in range(size_in)]
		self._outvalues=[default_value for i in range(size_out)]
	def get_outvalues(self, valnames):
		#The other nasty part of the thing
		outvals={}
		for val in valnames:
			valname = val[1]
			idx=int(valname[6:])
			outvals[valname] = self._outvalues[idx]
		return outvals
	def set_outvalues(self, outvalues):
		self._outvalues = outvalues
		#print "outvalues set to", outvalues
	def set_invalues(self, values_sets):
		for valset in values_sets:
			#here is the nasty part of the thing
			name=valset[0]
			value=valset[1]
			idx=int(valset[0][5:])
			self._invalues[idx]=float(value)
	def get_invalues(self):
		return self._invalues
	def print_values(self):
		print "Input values :", ["%.3f" %val for val in self._invalues]
		print "Output values :", ["%.3f" %val for val in self._outvalues]
UDP_nbSend=0
class UDPControlHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		global UDP_nbSend
		#RTlab sends some data !!!
		raw_recv = self.request[0].strip()
		#First of all we send him new stuff
		vals=dataHandler.get_invalues()
		data_send = tuple([1,UDP_nbSend,8*len(vals)]+vals)
		raw_send = struct.pack(UDP_format_in, *data_send)
		self.request[1].sendto(raw_send, (UDP_send_host,UDP_send_port))
		UDP_nbSend+=1
		
		#print "recv:", data_recv
		#print "send:", data_send
		data_recv = list(struct.unpack(UDP_format_out, raw_recv))
		dataHandler.set_outvalues(data_recv[3:])

parser = optparse.OptionParser(version=version)
parser.add_option('-P', default=8000, type="int", help="Port number for http")
parser.add_option('-R', default=50000, type="int", help="Port number for communication with opalRT")
parser.add_option('-I', default=16, type="int", help="Number of float values sent to opal")
parser.add_option('-O', default=16, type="int", help="Number of float values sent by opal")
parser.add_option('-s', '--silent', action="store_true",default=False, help="Silent mode (no-prompt)", dest="silent")
argopt, arg_remainder = parser.parse_args()

UDP_format_in='<hih'+str(argopt.I)+'d'
# UDP_format_in='<ddd'+str(argopt.I)+'d'
UDP_format_out='<hih'+str(argopt.O)+'d'
# UDP_format_out='<ddd'+str(argopt.O)+'d'
http_port=argopt.P
opal_port=argopt.R

dataHandler = MyDataHandler(argopt.I, argopt.O, 0.0)

print "Launching UDP server for opal com ...",
controlServer = SocketServer.UDPServer(('0.0.0.0', 50000), UDPControlHandler)
tUDP=threading.Thread(target=controlServer.serve_forever)
tUDP.setDaemon(True)
tUDP.start()
print "Ok"

print "Launching HTTP webserver ...",
httpServer = BaseHTTPServer.HTTPServer(('0.0.0.0', http_port), MyHttpHandler)
tHttp=threading.Thread(target=httpServer.serve_forever)
tHttp.setDaemon(True)
tHttp.start()
print "Ok"
if argopt.silent:
	while(running):
		time.sleep(1)
else:
	while(running):
		inpt_raw=raw_input('opalWebSrv>')
		inpt=inpt_raw.split()
		if len(inpt)==0:
			pass
		elif inpt[0]=='l':
			dataHandler.print_values()
		elif inpt[0]=='h':
			print "Enter l for listing values"
			print "Enter q for stopping the server"
			print "Enter v for version information"
			print "Enter hl [on/off] for (des)activating http logging"
		elif inpt[0]=="v":
			print "opalWebSrv version" + version
		elif inpt[0]=="q":
			break
		elif inpt[0]=="hl":
			if len(inpt)>1:
				activateHttpLogging(inpt[1])
		else:
			print "Unknown command : '"+inpt_raw+"'"

print "Server stopped"
