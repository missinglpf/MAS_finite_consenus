# import urllib2
# set_url = "http://169.254.35.122:8000/asyncsrv/" + 'set?valin0=1.0'
# print set_url
# req = urllib2.Request(url=set_url)
# f = urllib2.urlopen(req)
# response = f.read()
# print response
import time
import urllib2
import json
# print time.time()
import datetime
import urllib2
import numpy as np

a=  {2 : ["localhost", 8002],
		4: ["localhost", 8004]}
for i in a:
	print(i)
a.pop(2, None)
print(a.keys())
print(abs(1-2))

print("s" is not None)