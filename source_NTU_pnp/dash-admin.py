import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, State, Output, Event
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


# agents_wired = [[1, "localhost", 8001],
#                         [2, "localhost", 8002],
#                         [3, "localhost", 8003],
#                         [4, "localhost", 8004]]

agents_wired = [[1, "192.168.127.53", 8000],
                        [2, "192.168.127.54", 8000],
                        [3, "192.168.127.55", 8000],
                        [4, "192.168.127.56", 8000]]


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
# command = ""

k1 = 1
k2 = 5
k3 = 1
alpha = 0.2
beta = 2*alpha/(1+alpha)
gama = 0.5
kw = 10
kv = 10

app = dash.Dash()
global display
display = ''
app.layout = html.Div(children=[
    html.Div(id='output1'),
    html.Div(id='output2'),
    html.Div(id='output3'),
    html.Div(id='output4'),
    html.Div(id='iter'),
    html.Button(id='b_on', children='turn on'),
    html.Button(id='b_start', children='start'),
    html.Button(id='b_ws', children='run webserver'),
    html.Button(id='b_stop', children='shutdown'),

    html.Label('k1'),
    dcc.Input(id='i_k1', value='{}'.format(k1), type='text'),

    html.Label('k2'),
    dcc.Input(id='i_k2', value='{}'.format(k2), type='text'),

    html.Label('kw'),
    dcc.Input(id='i_kw', value='{}'.format(kw), type='text'),

    html.Label('kv'),
    dcc.Input(id='i_kv', value='{}'.format(kv), type='text'),

    html.Button(id='b_set', children='turn parameters'),
    html.Div(id='output'),
])

@app.callback(
    Output('output1', 'children'),
    [Input('b_on', 'n_clicks')])
def clicks1(n_clicks):
    global display
    if n_clicks>0:
        subprocess.Popen("run.bat", creationflags=subprocess.CREATE_NEW_CONSOLE)
        # display = 'turn on all agents'
        return 'turn on all agents'

@app.callback(
    Output('output2', 'children'),
    [Input('b_start', 'n_clicks')])
def clicks2(n_clicks):
    if n_clicks>0:
        for p in agents_wired:
            p[-1].start_consensus(finite_consensus_pb2.EmptyRequest())
        return 'started all agents'

@app.callback(
    Output('output3', 'children'),
    [Input('b_stop', 'n_clicks')])
def clicks3(n_clicks):
    if n_clicks>0:
        for p in agents_wired:
            p[-1].remote_shutdown(finite_consensus_pb2.EmptyRequest())
        return 'stop all agents'

@app.callback(
    Output('output4', 'children'),
    [Input('b_ws', 'n_clicks')])
def clicks4(n_clicks):
    if n_clicks>0:
        subprocess.Popen("python ..\\opalWebsrv\\opalWebSrv.py -I12 -O20", creationflags=subprocess.CREATE_NEW_CONSOLE)
        return 'run webserver'

@app.callback(
    Output('output', 'children'),
    [Input('b_set', 'n_clicks')],
    state=[State('i_k1', 'value'),
           State('i_k2', 'value'),
           State('i_kw', 'value'),
           State('i_kv', 'value')
    ]
)
def compute(n_clicks, input1, input2, input3, input4):
    if n_clicks>0:
        k1 = float(input1)
        k2 = float(input2)
        kw = float(input3)
        kv = float(input4)
        for p in agents_wired:
            req = finite_consensus_pb2.SetParas(k1=k1, k2=k2, k3=k3, alpha=alpha, beta=beta, gama=gama, kw=kw, kv=kv)
            p[-1].set_parameters(req)
        return 'set parameters'

app.run_server()



# @app.callback(
#     Output(component_id='my-div', component_property='children'),
#     [Input('submit', 'n_clicks')],
#     state=[State('my-id','value')]
# )
# def compute(n_clicks, input1):
#     if input1 == "start":
#         for p in agents_wired:
#             p[-1].start_consensus(finite_consensus_pb2.EmptyRequest())
#         return "started all agents"

#     elif input1 == "stop":
#         for p in agents_wired:
#             p[-1].remote_shutdown(finite_consensus_pb2.EmptyRequest())
#         return "stop all agents"

#     elif input1 == "on":
#         subprocess.Popen("run.bat", creationflags=subprocess.CREATE_NEW_CONSOLE)
#         return "turned on all agents"

#     elif input1 == "ws":
#         subprocess.Popen("python ..\\opalWebsrv\\opalWebSrv.py -I12 -O20", creationflags=subprocess.CREATE_NEW_CONSOLE)
#         return "run webserver"

    # elif input_value == "set":
    #     check = True
    #     while check:
    #         para = raw_input("Which parameter you want to modify? ")
    #         value = raw_input("Value: ")
    #         if para == "k1":
    #             k1 = float(value)
    #         elif para == "k2":
    #             k2 = float(value)
    #         elif para == "k3":
    #             k3 = float(value)
    #         elif para == "alpha":
    #             alpha = float(value)
    #         elif para == "gama":
    #             gama = float(value)
    #         elif para == "kw":
    #             kw = float(value)
    #         elif para == "kv":
    #             kv = float(value)
    #         else:
    #             print "you can only choose k1, k2, k3, alpha or gama"
    #             break
    #         ask = raw_input("Do you want to modify another parameter?(y/n)  ")
    #         if ask == "n":
    #             check = False
    #             beta = 2 * alpha / (1 + alpha)
    #             for p in agents_wired:
    #                 req = finite_consensus_pb2.SetParas(k1=k1, k2=k2, k3=k3, alpha=alpha, beta=beta, gama=gama, kw=kw, kv=kv)
    #                 p[-1].set_parameters(req)
    #             print "sent request"
    # return 'You\'ve entered "{}"'.format(input_value)




