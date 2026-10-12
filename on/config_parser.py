## this file reads the config file and makes the adj list for the graph. 

import sys


def read_config(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            rows.append([int(x) for x in line.split()])

    n = len(rows) + 1                  
    graph = [[-1] * n for _ in range(n)]

    for i in range(n):
        graph[i][i] = 0

    for i, row in enumerate(rows):
        if len(row) != n - 1 - i:
            raise ValueError("row %d has %d entries, expected %d" % (i, len(row), n - 1 - i)) # sanity check
        for k, cost in enumerate(row):
            if cost == 0 or cost < -1:
                raise ValueError("invalid cost %d in row %d" % (cost, i)) # sanity check 
            j = i + 1 + k                  
            graph[i][j] = cost
            graph[j][i] = cost  

    return graph


def to_adj_list(graph):
    adj = {}
    for i in range(len(graph)):
        adj[chr(65 + i)] = [(chr(65 + j), graph[i][j])
                            for j in range(len(graph)) if j != i and graph[i][j] > 0]
    return adj


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: config_parser.py <config>")
        sys.exit(1)

    g = read_config(sys.argv[1])
    ## we print for debugging purposes
    print("adj list:")
    for node, nbrs in to_adj_list(g).items():
        print(node,":", nbrs)