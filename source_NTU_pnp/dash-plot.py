import dash
from dash.dependencies import Output, Event
import dash_core_components as dcc
import dash_html_components as html
import plotly
import random
import plotly.graph_objs as go
from collections import deque
import urllib2
import json
import datetime

X = deque(maxlen=1000)
X.append(50)
Y = deque(maxlen=1000)
Y.append(50)
Y1 = deque(maxlen=1000)
Y1.append(50)
Y2 = deque(maxlen=1000)
Y2.append(50)
Y3 = deque(maxlen=1000)
Y3.append(50)


app = dash.Dash(__name__)
app.layout = html.Div(
    [
        dcc.Graph(id='live-graph'),
        dcc.Interval(
            id='graph-update',
            interval=100,
            n_intervals=0
        ),
    ]
)

tic = datetime.datetime.now()

@app.callback(Output('live-graph', 'figure'),
              events=[Event('graph-update', 'interval')])
def update_graph_scatter():
    X.append((datetime.datetime.now()-tic).total_seconds())
    url = "http://localhost:8000/asyncsrv/get?name0=valout16&name1=valout17&name2=valout18&name3=valout19"
    req = urllib2.Request(url=url)
    f = urllib2.urlopen(req, timeout=0.02)
    response = f.read()
    d = json.loads(response)
    val = d['valout16']
    val1 = d['valout17']
    val2 = d['valout18']
    val3 = d['valout19']
    # Y.append(random.random() * 100)
    Y.append(val)
    Y1.append(val1)
    Y2.append(val2)
    Y3.append(val3)
    # print(val)

    data = plotly.graph_objs.Scatter(
            x=list(X),
            y=list(Y),
            name='f1',
            mode='lines'
            )
    data1 = plotly.graph_objs.Scatter(
        x=list(X),
        y=list(Y1),
        name='f2',
        mode='lines'
    )
    data2 = plotly.graph_objs.Scatter(
        x=list(X),
        y=list(Y2),
        name='f3',
        mode='lines'
    )
    data3 = plotly.graph_objs.Scatter(
        x=list(X),
        y=list(Y3),
        name='f4',
        mode='lines'
    )
    # print(list(Y))
    return {'data': [data, data1, data2, data3],
            # 'layout': go.Layout(xaxis=dict(range=[min(X),max(X)]), yaxis=dict(range=[min(Y),max(Y)]),)
            }



if __name__ == '__main__':
    app.run_server(debug=True, port=10091)