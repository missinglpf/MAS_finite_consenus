#! /usr/bin/python
import struct
import socket
the_format='<hih5d'
the_format1='<hih5d'
vals=(1,2,3,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,11.,12.,13.,14.,15.,16.,17.,18.,19.,20)
vals=(1,2,3,1.,2.,3.,4.,5.)
UDP_IP='192.168.127.100'
UDP_PORT=50000
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
d4= struct.pack(the_format, *vals)
print "Sending : ", vals
sent=sock.sendto(d4, (UDP_IP, UDP_PORT))
data,server=sock.recvfrom(4096)
print "Received :", struct.unpack(the_format1, data)
sock.close()
