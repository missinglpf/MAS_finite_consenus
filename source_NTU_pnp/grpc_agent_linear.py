import threading

import time
from concurrent import futures
import grpc
import finite_consensus_pb2
import finite_consensus_pb2_grpc
import admin_pb2
import admin_pb2_grpc
import json
from optparse import OptionParser
import os
import sys
import logging
import csv
import datetime
import re
from numpy import *
from ReadConfigFile import ReadConfiguration
import datetime
import urllib2
# sys.path.append('D:/phd/These_asys/source/nlopt_test/admm/opf_pypower')

# algorithm events
start_event = threading.Event()
all_values_event = threading.Event()
# system events
# agent_enabled_event = threading.Event()

# system locks
measurement_lock = threading.Lock()  # manages the access to the measurement signals
references_lock = threading.Lock()  # manages the access to the reference signals
values_lock = threading.Lock()  # manages the access to variables

# the grpc server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))

# flag for stopping the agent
running = True

# variables for timing the performance of the agent
rpc_counter = 0
rpc_total_time = 0
opal_total_time = 0
opal_counter = 0
opt_total_time = 0
opt_counter = 0
trigger_counter = 0

# measurement signals of the agent
f_meas = 0.0
P_meas = 0.0
SOC_meas = 0.0
V_meas = 0.0
Q_meas = 0.0

# in case the communication with OPAL will have some errors, count them
opal_com_error_count = 0

admin_ip = "localhost"
admin_port = 9000
MAX_ADMIN_COMM_RETRY = 10 # number of communication retries, in case of failing to contact the admin
MAX_OPAL_COMM_RETRY = 10  # number of communication retries, in case of failing to contact OPAL-RT
MEASUREMENTS_TO_ADMIN_DOWNSAMPLE = 500  # send to the admin each 500th measurement taken from OPAL-RT
# MEASUREMENTS_TO_NEIGH_DOWNSAMPLE = 20  # send to the neighbours each 20th measurement taken from OPAL-RT
# TRIGGER_SAMPLES = 50  # number of samples that have to meet a condition before taking any decision
DATA_LOG_PERIOD = 1  # write a line to the data_log_file every second

# global variables
f_received = {}
Eta_received = {}
SOC_received = {}
V_received = {}
Q_received = {}
count_received = {}
f_ref = 50
V_ref = 230*sqrt(2)

#results
Uw = 0.0
Ue = 0.0
Uq = 0.0

class AgentServer(finite_consensus_pb2_grpc.AgentServicer):
    # ========================== Functions for the RPC server that can be called remotely
    # starts the admm algorithm
    def start_consensus(self, request, context):
        try:
            start_event.set()
            print "command START from admin to ", str(config.me[0][0])
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('FAILED'), message=exc.message)

    # function called by the neighbours to set their corresponding values
    def set_values(self, request, context):
        try:
            set_local_values(request.f, request.P, request.SOC, request.V, request.Q, request.agent_id)
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('FAILED'), message=exc.message)

    # shuts down the agent remotely
    def remote_shutdown(self, request, context):
        global running
        try:
            print "command STOP from admin to ", str(config.me[0][0])
            running = False
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('FAILED'), message=exc.message)

    #set parameters
    def set_parameters(self, request, context):
        global k1, k2, k3, alpha, beta, gama, kw, kv
        try:
            print "set parameters from admin to ", str(config.me[0][0])
            k1 = request.k1
            k2 = request.k2
            k3 = request.k3
            alpha = request.alpha
            beta = request.beta
            gama = request.gama
            kw = request.kw
            kv = request.kv
            print "k1=", k1, ", k2=", k2, ", k3=", k3, ", alpha=", alpha, ", beta=", beta, ", gama=", gama, ", kw=", kw, ", kv=", kv
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return finite_consensus_pb2.CommReply(status=finite_consensus_pb2.OperationStatus.Value('FAILED'),
                                                  message=exc.message)

def init_opal():
    global k1, k2, k3, alpha, beta, gama, kw, kv
    # global Eta_me, SOC_me

    # Eta_me = 0
    # SOC_me = 0
    k1 = config.k1
    k2 = config.k2
    k3 = config.k3
    alpha = config.alpha
    beta = config.beta
    gama = config.gama
    kw = config.kw
    kv = config.kv

    # print "initial send to opal"
    set_url = config.url_opal + 'set?valin' + \
              str(config.opal_set_ids["Uw"]) + '=' + str(0.0) \
              + '&valin' + str(config.opal_set_ids["Ue"]) + '=' + str(0.0) \
              + '&valin' + str(config.opal_set_ids["Uq"]) + '=' + str(0.0)
    logging.info(set_url)
    req = urllib2.Request(url=set_url)
    f = urllib2.urlopen(req)
    response = f.read()
    # distribute_values()
    if 'Ok' not in response:
        notify_administrator("Cannot set initial voltage & power references in OPAL-RT")

def pool_opal(start_event):
    logging.info("start pool opal")
    if not start_event.isSet():
        logging.info("Waiting for the admin to be enabled")
    start_event.wait()  # blocking call until the enable event is detected
    global opal_com_error_count
    global f_meas, P_meas, SOC_meas, V_meas, Q_meas  # measurement signals
    while running:
        # make access to shared resources thread safe
        key_f = "valout" + str(config.opal_get_ids["f"])
        key_P = "valout" + str(config.opal_get_ids["P"])
        key_SOC = "valout" + str(config.opal_get_ids["SOC"])
        key_V = "valout" + str(config.opal_get_ids["V"])
        key_Q = "valout" + str(config.opal_get_ids["Q"])
        # compose the URL for the webserver
        get_url = config.url_opal + 'get?' + 'name0=' + key_f + '&' + 'name1=' + key_P + \
                  '&' + 'name2=' + key_SOC + '&' + 'name1=' + key_V + '&' + 'name1=' + key_Q

        req = urllib2.Request(url=get_url)
        try:
            tic = datetime.datetime.now()
            f = urllib2.urlopen(req, timeout=0.03)
            toc = datetime.datetime.now()
            response = f.read()
            delta = (toc - tic).total_seconds()
            # print(delta)
            get_opal_statistics(delta)
            d = json.loads(response)
            with measurement_lock:   # measurements are accessed from several threads, therefore they need to be protected
                f_meas = float(d[key_f])
                P_meas = float(d[key_P])
                SOC_meas = float(d[key_SOC])
                V_meas = float(d[key_V])
                Q_meas = float(d[key_Q])
        except Exception as exc:
            print("timeout receive from ws")
            # opal_com_error_count += 1
            # if opal_com_error_count >= MAX_OPAL_COMM_RETRY:
            #     notify_administrator("There seems to be a problem with the WEB-SERVER")
            #     notify_administrator(exc.message)
            #     opal_com_error_count = 0
            logging.critical(exc.message)

        # time.sleep(config.ts_opal)

    # reschedule the function to start again
    # t = threading.Timer(config.ts_opal, pool_opal, args=(start_event,))
    # t.name = "measurement-thread"
    # t.daemon = True
    # if running:
    #     t.start()

def get_optimization_statistics(delta):
    global opt_total_time, opt_counter
    opt_total_time += delta
    opt_counter += 1


def get_rpc_statistics(delta):
    global rpc_total_time, rpc_counter
    rpc_total_time += delta
    rpc_counter += 1

def get_opal_statistics(delta):
    global opal_total_time, opal_counter
    opal_total_time += delta
    opal_counter += 1
    # if opal_counter % MEASUREMENTS_TO_ADMIN_DOWNSAMPLE == 0:
    #     notify_administrator("measurements")

# ========================== finite consensus Algorithm
def consensus(all_values_event):
    global f_meas, P_meas, SOC_meas, V_meas, Q_meas
    global f_received, Eta_received, SOC_received, V_received, Q_received
    global k1, k2, k3, alpha, beta, gama, kw, kv
    global f_ref, V_ref
    # inte = 1
    while running:

        logging.debug('Waiting for consensus_start event')
        start_event.wait()  # blocking wait call until the event is detected
        # notify_administrator("admm_started")
        # distribute measurement values to the neighburs
        distribute_values()
        # wait to receive all values from the neighbours
        logging.info(" Waiting to receive all values")
        all_values_event.wait()
        # Distributed Frequency Recovery
        Uw_1 = 0
        Uw_2 = 0
        Ue = 0
        # Eta_me = -(1 / 3600) * config.KE * (P_meas / config.CE)
        Uq_1 = 0
        Uq_2 = 0
        for nei in config.partners:
            # nei_idx = config.all_ids.index(nei[0])
            # Uw_1 += f_received[nei[0]] - f_received[config.me[0][0]]

                    # * config.A[nei_idx]
            # Uw_2 += (f_received[nei_idx] - f_meas) * config.A[nei_idx]
            Uw_1 += (abs(f_received[nei[0]] - f_received[config.me[0][0]]) ** gama) * sign(
                f_received[nei[0]] - f_received[config.me[0][0]])

            # Ue += -k2 * (Eta_received[nei[0]] - Eta_received[config.me[0][0]]) \
            #       - k1 * (SOC_received[nei[0]] - SOC_received[config.me[0][0]])

            Ue += -k2 * (abs(Eta_received[nei[0]] - Eta_received[config.me[0][0]]) ** beta) * sign(
                Eta_received[nei[0]] - Eta_received[config.me[0][0]]) \
                  - k1 * (abs(SOC_received[nei[0]] - SOC_received[config.me[0][0]]) ** alpha) * sign(
                SOC_received[nei[0]] - SOC_received[config.me[0][0]])
                  # * config.A[nei_idx]
            Uq_1 += (abs(V_received[nei[0]] - V_received[config.me[0][0]]) ** gama) * sign(
                V_received[nei[0]] - V_received[config.me[0][0]])
            # Uq_1 += V_received[nei[0]] - V_received[config.me[0][0]]
                    # * config.A[nei_idx]
            # Uq_2 += (V_received[nei_idx] - V_meas) * config.A[nei_idx]

        Uw_1 += f_ref - f_received[config.me[0][0]]
        # Uw_2 += (f_ref - f_meas)
        Uw = kw * (Uw_1 + Uw_2)

        Uq_1 += V_ref - V_received[config.me[0][0]]
        # Uq_2 += (V_ref - V_meas)
        Uq = kv * (Uq_1 + Uq_2)
        #send to opal
        send_to_opal(Uw, Ue, Uq)
        # data_snapshot_to_file()
        reset()

        logging.info("Agent " + str(config.me[0][0]) + ": a consensus step finished ")

        # print(inte)
        # inte += 1
        # re-initialize the buffers
        # init_admm_buffers()

def reset():
    global f_received, Eta_received, SOC_received, V_received, Q_received, count_received
    # global Eta_me, SOC_me
    all_values_event.clear()
    count_received = {}
    f_received = {}
    Eta_received = {}
    SOC_received = {}
    V_received = {}
    Q_received = {}
    # Eta_me = 0
    # SOC_me = 0

def set_local_values(f, Eta, SOC, V, Q, agent_id):
    # idx = config.all_ids.index(agent_id)  # get the position in the vector where this value should go
    with values_lock:
        try:
            f_received[agent_id] = f
            Eta_received[agent_id] = Eta
            SOC_received[agent_id] = SOC
            V_received[agent_id] = V
            Q_received[agent_id] = Q
            count_received[agent_id] = 1.0

            logging.debug("Agent " + str(config.me[0][0]) + ": Values" +
                          "-> from Agent " + str(agent_id))
            # received all the information
            if sum(count_received.values()) == config.n:
                logging.info("Agent " + str(config.me[0][0]) + ": Received all info")
                all_values_event.set()
        except KeyError as exc:
            logging.critical(
                "Agent " + str(config.me[0][0]) + ": WTFFF!!! ")
            logging.critical(exc.message)

def distribute_values():
    # global Eta_me, SOC_me
    global f_meas, P_meas, SOC_meas, V_meas, Q_meas
    # Eta_me = -(1 / 3600) * config.KE * (P_meas / config.CE)
    Eta_me = P_meas
    f_me = f_meas
    V_me = V_meas
    Q_me = Q_meas
    SOC_me = SOC_meas

    set_local_values(f_me, Eta_me, SOC_me, V_me, Q_me, config.me[0][0])

    for p in config.partners:
        # idx = config.all_ids.index(p[0])  # get the index of the neighbour
        try:
            # SOC_me = SOC_meas
            req = finite_consensus_pb2.SetValues(f=f_me, P=Eta_me, SOC=SOC_me, V=V_me, Q=Q_me,
                                                 agent_id=config.me[0][0])
            tic = datetime.datetime.now()
            p[-1].set_values(req)  # call RPC for each neighbour
            toc = datetime.datetime.now()
            delta = (toc - tic).total_seconds()
            get_rpc_statistics(delta)
            logging.debug("Agent " + str(config.me[0][0]) + " sent values to Agent " + str(p))
        except Exception as exc:
            logging.critical(
                "Agent " + str(config.me[0][0]) + ": Can't contact agent " + str(p[0]) )
            logging.exception(exc.message)
    logging.info("Agent " + str(config.me[0][0]) + ": I finished distributing all values")

# def data_snapshot_to_file():
#     global x, nu, z, admm_it, config
#     try:
#         if not os.path.isfile(dataFile):
#             header = ['Id', 'Time']
#             header += ['X_real']
#             header += ['X_imag']
#             header += ['Nu_real']
#             header += ['Nu_imag']
#             header += ['Z_real']
#             header += ['Z_imag']
#             header += ['P']
#             header += ['Q']
#             with open(dataFile, 'w') as f:
#                 writer = csv.writer(f)
#                 writer.writerow(header)
#
#         fields = []
#         # if include_admm_data:
#         fields += [admm_it]
#         # print(fields)
#         fields += [x[admm_it][0]]
#         # print(fields)
#         fields += [x[admm_it][config.n]]
#         fields += [nu[admm_it][0]]
#         fields += [nu[admm_it][config.n]]
#         fields += [z[admm_it][0]]
#         fields += [z[admm_it][config.n]]
#         # print('b')
#         # P = V.*(G*V)
#         # pz = np.multiply(z[admm_it], np.dot(config.G, z[admm_it]))
#         x1 = asmatrix(x[admm_it])
#         p = x1 * config.z_pk * x1.T + config.pd
#         q = x1 * config.z_qk * x1.T + config.qd
#         # print(p)
#         # print(p[0,0])
#         fields += [p[0,0]]
#         fields += [q[0,0]]
#         # print(fields)
#
#         # else:
#         #     fields += [0] * 9  # add zeros to the file in order to create a consistent .csv table
#         with open(dataFile, 'a') as f:
#             writer = csv.writer(f)
#             time_stamp = time.time()
#             line = [config.me[0][0], time_stamp]
#             line += ['{:3.4f}'.format(xval) for xval in fields]
#             writer.writerow(line)
#     except Exception as ex:
#         print(ex.message)

# def log_experiment_data_loop():
#     # if not admm_running:
#     #     data_snapshot_to_file(include_admm_data=False)
#     t = threading.Timer(DATA_LOG_PERIOD, log_experiment_data_loop)
#     t.daemon = True
#     t.name = "log-thread"
#     logging.info("log thread")
#     if running:
#         t.start()

def send_to_opal(Uw, Ue, Uq):
    set_url = config.url_opal + 'set?valin' + \
              str(config.opal_set_ids["Uw"]) + '=' + str(Uw) \
              + '&valin' + str(config.opal_set_ids["Ue"]) + '=' + str(Ue) \
              + '&valin' + str(config.opal_set_ids["Uq"]) + '=' + str(Uq)
    try:
        req = urllib2.Request(url=set_url)
        tic = datetime.datetime.now()
        f = urllib2.urlopen(req, timeout=0.03)
        toc = datetime.datetime.now()
        delta = (toc - tic).total_seconds()
        # print(delta)
        response = f.read()
        if 'Ok' not in response:
            notify_administrator("Cannot send the new references to the OPAL-RT")
        logging.info("sent to opal")
    except Exception as exc:
        print("timeout send to server")
        # opal_com_error_count += 1
        # if opal_com_error_count >= MAX_OPAL_COMM_RETRY:
        #     notify_administrator("There seems to be a problem with the WEB-SERVER")
        #     notify_administrator(exc.message)
        #     opal_com_error_count = 0
        logging.critical(exc.message)

# ========================== Functions for communicating with the administrator and data logging
# handles the communication with the administrator
def notify_administrator(topic):
    comm_error_count = 0
    while comm_error_count < MAX_ADMIN_COMM_RETRY:
        try:
            if topic is "online":
                req = admin_pb2.AgentRequest(agent_id=config.me[0][0])
                admin_stub.agent_online(req)
            elif topic is "offline":
                req = admin_pb2.AgentRequest(agent_id=config.me[0][0])
                admin_stub.agent_offline(req)
            elif topic is "results":
                req = admin_pb2.Results(agent_id=config.me[0][0], avg_consensus_time=opt_total_time * 1000 / opt_counter,
                                            avg_rpc_time=rpc_total_time * 1000 / rpc_counter,
                                        Uw=Uw, Ue=Ue, Uq=Uq)
                admin_stub.agent_results(req)
            elif topic is "measurements":
                req = admin_pb2.Measurements(agent_id=config.me[0][0], avg_opal_time=opal_total_time * 1000 / opal_counter,
                                             f_meas=f_meas, P_meas=P_meas, SOC_meas=P_meas, V_meas=V_meas, Q_meas=Q_meas)
                admin_stub.agent_measurements(req)
            else:  # if topic not in list send a general message to the admin
                req = admin_pb2.GenericMessage(agent_id=config.me[0][0], text=topic)
                admin_stub.agent_general_use_message(req)
            break
        except Exception as exc:
            logging.error("Agent " + str(config.me[0]) + ": Can't contact the administrator for sending data")
            comm_error_count += 1
            if comm_error_count >= MAX_ADMIN_COMM_RETRY:
                logging.critical("Agent " + str(config.me[0]) + ": Something is definetly wrong. ABORTING!")
                logging.exception(exc.message)
            else:
                logging.info(
                    "Agent " + str(config.me[0]) + ": The communication might be busy. I will retry in lamda10 ms!")
                time.sleep(0.01)
#
# def log_experiment_data_loop():
#     if not start_event.isSet():
#         logging.info("Waiting for the agent to be enabled")
#     start_event.wait()
#     t = threading.Timer(DATA_LOG_PERIOD, log_experiment_data_loop)
#     t.daemon = True
#     t.name = "log-thread"
#     if running:
#         t.start()

optp = OptionParser()
optp.add_option("-f", "--filename", dest="jsonFile",
                help="json file containing the configuration of the agent")
opts, args = optp.parse_args()
if opts.jsonFile is None:
    opts.jsonFile = raw_input("Name of the json file containing the configuration of the agent:")

log = "logs\log_A_" + re.search(r'\d+', opts.jsonFile).group() + ".txt"
print log
dataFile = "data_A_" + re.search(r'\d+', opts.jsonFile).group() + ".csv"
print dataFile
# log to file
logging.basicConfig(level=logging.DEBUG,  filename=log, filemode="w",
                    format='%(asctime)s (%(threadName)-9s) %(levelname)s: %(message)s')

logging.info("Reading the configuration file")
# read the configuration of the agent
# print(opts.jsonFile)
config = ReadConfiguration(opts.jsonFile)

logging.info("Opening communication channels to neighbours")
# open communication channels towards the neighbours
for p in config.partners:
    channel = grpc.insecure_channel(p[1] + ":" + str(p[2]))
    stub = finite_consensus_pb2_grpc.AgentStub(channel)
    p += [stub]  # store the rpc stub in the config.partners collection

logging.info("Opening the communication channels to the admin")
# open the communication channel to the admin
admin_channel = grpc.insecure_channel(admin_ip + ":" + str(admin_port))
admin_stub = admin_pb2_grpc.adminStub(channel=admin_channel)

logging.info("Starting the measurement thread")
# configure and start the program threads
meas_thread = threading.Thread(name='measurement-thread', target=pool_opal, args=(start_event,))
meas_thread.daemon = True
meas_thread.start()  # start the measurement thread


# logging.info("Starting the data loging thread")
# log_thread = threading.Thread(name='log-thread', target=log_experiment_data_loop)
# log_thread.daemon = True
# log_thread.start()  # start the log thread

logging.info("Starting the consensus thread")
admm_ctrl_thread = threading.Thread(name='consensus-thread', target=consensus,
                               args=(all_values_event,))
admm_ctrl_thread.daemon = True
admm_ctrl_thread.start()  # start the admm thread

# create the RPC server for the agent
logging.info("Starting the agent's RPC server")
finite_consensus_pb2_grpc.add_AgentServicer_to_server(AgentServer(), server)
server.add_insecure_port(config.me[0][1] + ":" + str(config.me[0][2]))
server.start()
logging.info("Agent " + str(config.me[0][0]) + " starting at:" + config.me[0][1] + ":" + str(config.me[0][2]))
time.sleep(2)
logging.info("Setting the initial values in OPAL-RT")
# set the voltage in the opal

init_opal()
# notify the administrator that I am online
notify_administrator("online")
time.sleep(2)

while running:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        running = False

notify_administrator("offline")
print "stop"
server.stop(0)