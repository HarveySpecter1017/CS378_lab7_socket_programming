import os
import select
import socket
import struct
import sys

from config_parser import read_config

PORT = 5000
POLL_SECS = 1.0

HDR = struct.Struct('!BH')     
TUP = struct.Struct('!4sHBB')       
MSG_CONNECT = 1
MSG_LINK_STATE = 2


def extract_messages(buf):
    """Cut complete messages off the front of buf.
    Returns (list of (type, body), leftover bytes)."""
    msgs = []
    while len(buf) >= HDR.size:
        mtype, blen = HDR.unpack_from(buf)
        if len(buf) < HDR.size + blen:
            break                
        msgs.append((mtype, buf[HDR.size:HDR.size + blen]))
        buf = buf[HDR.size + blen:]
    return msgs, buf


def handle_message(idx, mtype, body, nodes):
    """Returns True if a valid CONNECT was decoded and stored."""
    if mtype == MSG_CONNECT:
        if len(body) != 6:
            print("node %s: bad CONNECT length %d" % (chr(65 + idx), len(body)))
            return False
        ip = socket.inet_ntoa(body[:4])           
        (port,) = struct.unpack('!H', body[4:6])  
        nodes[idx] = (ip, port)
        print("CONNECT from %s = %s:%d" % (chr(65 + idx), ip, port))
        return True
    print("node %s: unknown message type %d" % (chr(65 + idx), mtype))
    return False


def pack_tuple(nodes, j, cost):
    ip, port = nodes[j]
    return TUP.pack(socket.inet_aton(ip), port, j, cost)


def build_link_state(idx, graph, nodes):
    """Full LINK-STATE message for node idx: its own tuple (cost 0) + one per neighbour."""
    n = len(graph)
    body = pack_tuple(nodes, idx, 0)
    if idx < n:                                 
        for j in range(n):
            if j != idx and graph[idx][j] > 0 and nodes[j] is not None:
                body += pack_tuple(nodes, j, graph[idx][j])
    return HDR.pack(MSG_LINK_STATE, len(body)) + body


def send_link_state(conns, idx, graph, nodes):
    if conns[idx] is None or nodes[idx] is None:
        return
    msg = build_link_state(idx, graph, nodes)
    try:
        conns[idx].sendall(msg)
        print("sent LINK-STATE to %s (%d bytes): %s" % (chr(65 + idx), len(msg), msg.hex()))
    except OSError as e:
        print("send to %s failed: %s" % (chr(65 + idx), e))


def broadcast(conns, graph, nodes):
    for idx in range(len(conns)):
        send_link_state(conns, idx, graph, nodes)


def main():
    # step 1
    if len(sys.argv) != 3:
        print("usage: python3 oracle_node.py <config_file> <bind_ip>")
        sys.exit(1)
    path = sys.argv[1]
    bind_ip = sys.argv[2]
    if not os.path.isfile(path):
        print("config file not found:", path)
        sys.exit(1)

    # step 2
    graph = read_config(path)
    n = len(graph)
    print("loaded config: %d nodes" % n)

    # step 3
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((bind_ip, PORT))
    except OSError as e:
        print("cannot bind %s:%d: %s" % (bind_ip, PORT, e))
        sys.exit(1)
    srv.listen(32)
    print("listening on %s:%d" % (bind_ip, PORT))

    conns = []    
    bufs = []     
    nodes = []    
    started = False                
    mtime = os.stat(path).st_mtime  

    while True:
        live = [c for c in conns if c is not None]
        readable, _, _ = select.select([srv] + live, [], [], POLL_SECS)

        for s in readable:
            if s is srv:
                sock, addr = srv.accept()
                idx = len(conns)
                if idx >= 26:
                    print("too many connections, rejecting %s:%d" % addr)
                    sock.close()
                    continue
                conns.append(sock)
                bufs.append(b'')
                nodes.append(None)
                letter = chr(65 + idx)
                if idx < n:
                    print("accepted %s:%d as node %s" % (addr[0], addr[1], letter))
                else:
                    print("accepted %s:%d as node %s (not in config, island)" % (addr[0], addr[1], letter))
            else:
                idx = conns.index(s)
                data = s.recv(4096)
                if not data:
                    print("node %s disconnected" % chr(65 + idx))
                    s.close()
                    conns[idx] = None
                    bufs[idx] = b''
                    nodes[idx] = None
                else:
                    # step 5
                    print("node %s: recv %d bytes: %s" % (chr(65 + idx), len(data), data.hex()))
                    bufs[idx] += data
                    msgs, bufs[idx] = extract_messages(bufs[idx])
                    for mtype, body in msgs:
                        # step 6
                        if handle_message(idx, mtype, body, nodes):
                            # step 9
                            if started:
                                send_link_state(conns, idx, graph, nodes)   # late joiner / island
                            elif len(nodes) >= n and all(x is not None for x in nodes[:n]):
                                started = True
                                print("all %d nodes have sent CONNECT, sending LINK-STATE to everyone" % n)
                                broadcast(conns, graph, nodes)              # all N connected

        # step 4
        try:
            new_mtime = os.stat(path).st_mtime
        except OSError:
            new_mtime = mtime

        if new_mtime != mtime:
            mtime = new_mtime
            try:
                new_graph = read_config(path)
            except (ValueError, OSError) as e:
                print("config reload failed, keeping old graph:", e)
            else:
                if len(new_graph) != n:
                    print("node count changed, ignoring")
                else:
                    graph = new_graph
                    print("config changed:")
                    for row in graph:
                        print(row)
                    if started:
                        broadcast(conns, graph, nodes)    # step 9


if __name__ == '__main__':
    main()