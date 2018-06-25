from concurrent import futures
import grpc
import finite_consensus_pb2
import finite_consensus_pb2_grpc
import admin_pb2
import admin_pb2_grpc
import logging
from numpy import *
import subprocess
import os

running =True
# the grpc server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))

class adminServer(finite_consensus_pb2_grpc.AgentServicer):
    # ========================== Functions for the RPC server that can be called remotely

    def agent_online(self, request, context):
        try:
            print "Agent" + str(request.agent_id) + "online"
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('FAILED'), message=exc.message)

    def agent_offline(self, request, context):
        try:
            print "Agent" + str(request.agent_id) + "offline"
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('FAILED'), message=exc.message)

    def agent_general_use_message(self, request, context):
        try:
            print "Agent" + str(request.agent_id) + ":" + str(request.text)
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('SUCCESS'))
        except Exception as exc:
            logging.critical(exc.message)
            return admin_pb2.CommReply(status=admin_pb2.OperationStatus.Value('FAILED'), message=exc.message)


agents_wired = [[1, "localhost", 8001],
                        [2, "localhost", 8002],
                        [3, "localhost", 8003],
                        [4, "localhost", 8004]]

admin_ip = "localhost"
admin_port = 9000

# open communication channels towards the neighbours
for p in agents_wired:
    channel = grpc.insecure_channel(p[1] + ":" + str(p[2]))
    stub = finite_consensus_pb2_grpc.AgentStub(channel)
    p += [stub]
    print p

# create the RPC server for the agent

admin_pb2_grpc.add_adminServicer_to_server(adminServer(), server)
server.add_insecure_port(admin_ip + ":" + str(admin_port))
server.start()
command = ""

k1 = 1
k2 = 5
k3 = 1
alpha = 0.2
beta = 2*alpha/(1+alpha)
gama = 0.5
kw = 10
kv = 10

while running:
    try:
        command = raw_input("send command to all agents: ")
        # print command

        if command == "start":
            for p in agents_wired:
                p[-1].start_consensus(finite_consensus_pb2.EmptyRequest())
            print "sent request"

        elif command == "stop":
            for p in agents_wired:
                p[-1].remote_shutdown(finite_consensus_pb2.EmptyRequest())
            print "sent request"

        elif command == "on":
            subprocess.Popen("run.bat", creationflags=subprocess.CREATE_NEW_CONSOLE)

        elif command == "ws":
            subprocess.Popen("python ..\opalWebsrv\opalWebSrv.py -I12 -O20", creationflags=subprocess.CREATE_NEW_CONSOLE)

        elif command == "set":
            check = True
            while check:
                para = raw_input("Which parameter you want to modify? ")
                value = raw_input("Value: ")
                if para == "k1":
                    k1 = float(value)
                elif para == "k2":
                    k2 = float(value)
                elif para == "k3":
                    k3 = float(value)
                elif para == "alpha":
                    alpha = float(value)
                elif para == "gama":
                    gama = float(value)
                elif para == "kw":
                    kw = float(value)
                elif para == "kv":
                    kv = float(value)
                else:
                    print "you can only choose k1, k2, k3, alpha or gama"
                    break
                ask = raw_input("Do you want to modify another parameter?(y/n)  ")
                if ask == "n":
                    check = False
                    beta = 2 * alpha / (1 + alpha)
                    for p in agents_wired:
                        req = finite_consensus_pb2.SetParas(k1=k1, k2=k2, k3=k3, alpha=alpha, beta=beta, gama=gama, kw=kw, kv=kv)
                        p[-1].set_parameters(req)
                    print "sent request"

    except KeyboardInterrupt:
        running = False

print "stop"
server.stop(0)