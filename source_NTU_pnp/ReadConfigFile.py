import json

class ReadConfiguration:
    def __init__(self, file_name):
        with open(file_name) as json_data:
            d = json.load(json_data)
            # id, ip and port of this agent
            self.me = d["me"]
            # id, ip, port of communication partners
            self.partners = d["partners"]
            # all ids
            self.all_ids = [row[0] for row in (self.me + self.partners)]
            # self.all_ids.append(self.me[0])
            self.all_ids.sort()
            print(self.all_ids)
            self.my_idx = self.all_ids.index(self.me[0][0])
            # time step for pooling opal rt
            self.ts_opal = d["ts_opal"]
            # the url for the opal websrv
            self.url_opal = d["url_opal"]
            # the ids of the variables that the agent gets from OPAL RT
            self.opal_get_ids = d["opal_get_ids"]
            # the ids of the variables that the agent sets in OPAL RT
            self.opal_set_ids = d["opal_set_ids"]
            # the default values to set in OPAL RT at the beginning of the session
            self.opal_default_set = d["opal_default_set"]
            # print("test")
            # self.initial_values = d["initial_values"]
            # matrix
            self.A = d["A"]
            # print "test2"
            self.L = d["L"]
            # print(self.L)
            # number of neighbors
            self.n = len(self.all_ids)
            # print(self.n)
            # parameters
            self.k1 = d["k1"]
            self.k2 = d["k2"]
            self.k3 = d["k3"]
            self.kw = d["kw"]
            self.kv = d["kV"]
            self.gama = d["gama"]
            self.alpha = d["alpha"]
            self.beta = d["beta"]
            self.KE = d["KE"]
            self.CE = d["CE"]
            self.Kq = d["Kq"]
            # print("end config")
