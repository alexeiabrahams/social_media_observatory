import os
from ..config import HOME_DIR
from ..utilities.logic_ch4 import make_forward_network
import networkx as nx

OUTPUT_DIR = os.path.join(HOME_DIR, "PycharmProjects/smo/ch4/data")
SEED_LIST_NAMES = ["russian_disinfo"]
START_DATE = "2022-02-14"
END_DATE = "2022-03-15"

G = make_forward_network(SEED_LIST_NAMES, START_DATE, END_DATE)

nx.write_graphml(G, os.path.join(OUTPUT_DIR, "russian_disinfo_fwd_network.graphml"))
