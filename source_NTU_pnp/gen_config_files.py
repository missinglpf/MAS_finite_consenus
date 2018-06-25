import math
from numpy import *
import pprint
from scipy.sparse import *
import numpy as np

PATH = "../config/pnp/rpi"

N = 4 #number of agent
busIdx = [1, 2, 3, 4]


# ip address of the raspberry PI for the wired and wireless communication
PI_wired_addr = ['192.168.127.53', '192.168.127.54', '192.168.127.55', '192.168.127.56']
PI_wireless_addr = ['192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104']

#PI_addr = PI_wireless_addr  # use the wireless IP addresses to create the configuration files
PI_addr = PI_wired_addr  # use the wired IP addresses to create the configuration files
# PI_addr = ["localhost"]*N #localhost
bus2PI = range(0, 4)
bus2Port = [8000]*4
# bus2PI = ["localhost"]*13
# bus2Port = range(8001, 8005)
# url_opal = "http://169.254.35.121:8000/asyncsrv/"  # URL address of the opal5600 web server
# url_opal = "http://localhost:8000/asyncsrv/"  # URL address of the opal5000 web server
url_opal = "http://192.168.127.100:8000/asyncsrv/"  # URL address of the opal5600 web server
var1 = range(0, 4)  # indices of the first interface variable (f from Opal)
var2 = range(4, 8)  # indices of the second interface variable (P load from Opal)
var3 = range(8, 12)  # indices of the third interface variable (SOC) from Opal
var4 = range(12, 16)  # indices of the forth interface variable (V) from Opal
var5 = range(16, 20)  # indices of the fifth interface variable (Q) from Opal
var6 = range(20, 24)  # indices of the sixth interface variable (state) from Opal

## communication links
# fbus, tbus, delay[s], loss[%]
comm_links_default = [
        [1,    2],
        [1,    4],
        [2,    3],
        [3,    4]
    ]
comm_links = comm_links_default  # configuration of the communication links

ts_opal = 0.0005  # sampling time of the OPAL

A = [
    [0, 1, 0, 1],
    [1, 0, 1, 0],
    [0, 1, 0, 1],
    [1, 0, 1, 0]
]

L = 2*np.eye(N) - A

gama = 1
f = 50

# control gain
k1 = 3
k2 = 50
k3 = 100
kw = 1
kV = 1

alpha = 0.5
beta = 2*alpha/(1+alpha)

KE = [1, 1, 1, 1]
CE = [1e3, 1e3, 2e3, 2e3]
Kq = [1/1e4, 1/1e4, 0.5/1e4, 0.5/1e4]

Uw_init = 0.0
Ue_init = 0.0
Uq_init = 0.0

json_tmpl = '{{\n\t"me" : {}, ' \
            '\n\t"partners" : {},' \
            '\n\t"ts_opal" : {},' \
            '\n\t"url_opal" : "{}",' \
            '\n\t"opal_get_ids" : {{"f" : {}, "P" : {}, "SOC" : {}, "V" : {}, "Q" : {}, "state" : {}}},' \
            '\n\t"opal_set_ids" : {{"Uw" : {}, "Ue" : {}, "Uq" : {}}},' \
            '\n\t"opal_default_set" : {{"f" : {}, "P" : {}, "SOC" : {}, "V" : {}, "Q" : {}}},' \
            '\n\t"A" : {},' \
            '\n\t"L" : {},' \
            '\n\t"k1" : {:.10f},' \
            '\n\t"k2" : {:.10f},' \
            '\n\t"k3" : {:.10f},' \
            '\n\t"kw" : {:.10f},' \
            '\n\t"kV" : {:.10f},' \
            '\n\t"gama" : {:.10f},' \
            '\n\t"alpha" : {:.10f},' \
            '\n\t"beta" : {:.10f},' \
            '\n\t"KE" : {:.10f},' \
            '\n\t"CE" : {:.10f},' \
            '\n\t"Kq" : {:.10f}' \
            '\n}}'
cnt = 0
set_printoptions(precision=10)

f_def = '0'
P_def = '0'
SOC_def = '0'
V_def = str(230*sqrt(2))
V_def = 0
Q_def = '0'

for i in busIdx:
    ids = []
    c = 0
    partners = '['
    for row in comm_links:
        neigh = -1
        row_idx = comm_links.index(row)
        if int(row[0]) == i:
            neigh = row[1]
        if int(row[1]) == i:
            neigh = row[0]
        if neigh > -1:
            ids += [int(neigh)]
            s = '[{}, "{}", {}],\n\t\t'.format(int(neigh), PI_addr[bus2PI[busIdx.index(neigh)]],
                                                   bus2Port[busIdx.index(neigh)])
            partners += s
    partners = partners[:-4]
    partners += ']'
    ids = [i] + ids
    ids.sort()

    me = '[[{}, "{}", {}]]'.format(i, PI_addr[bus2PI[busIdx.index(i)]], bus2Port[busIdx.index(i)])

    a = '['
    l = '['
    for j in ids:
        a += '{:.10f}, '.format(A[busIdx.index(i)][busIdx.index(j)])
        l += '{:.10f}, '.format(L[busIdx.index(i)][busIdx.index(j)])
    a = a[:-2]
    l = l[:-2]
    a += ']'
    l += ']'

    json_dump = json_tmpl.format(me, partners, ts_opal, url_opal, var5[cnt], var1[cnt], var2[cnt], var3[cnt], var4[cnt], var6[cnt], var1[cnt], var2[cnt], var3[cnt],\
                                 f_def, P_def, SOC_def, V_def, Q_def, a, l, k1, k2, k3, kw, kV, gama, alpha, beta, KE[busIdx.index(i)], CE[busIdx.index(i)], Kq[busIdx.index(i)])
    file_name = PATH + '/config_A_{}.json'.format(i)
    config_file = open(file_name, 'w')
    config_file.write(json_dump)
    config_file.close()
    cnt += 1