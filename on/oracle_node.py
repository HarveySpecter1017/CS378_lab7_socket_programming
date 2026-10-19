import os
import select
import socket
import struct
import sys

from config_parser import read_config

PORT = 5000
POLL_SECS = 1.0

HDR = struct.Struct('!BH')          # [type:1B][length:2B], network byte order
TUP = struct.Struct('!4sHBB')       # one LINK-STATE tuple: ip(4) port(2) id(1) cost(1) = 8 bytes
MSG_CONNECT = 1
MSG_LINK_STATE = 2


def extract_messages(buf):
    """Cut complete messages off the front of buf.
    Returns (list of (type, body), leftover bytes)."""
    msgs = []
    while len(buf) >= HDR.size:
        mtype, blen = HDR.unpack_from(buf)
        if len(buf) < HDR.size + blen:
            break                       # body hasn't fully arrived, wait for more
        msgs.append((mtype, buf[HDR.size:HDR.size + blen]))
        buf = buf[HDR.size + blen:]
    return msgs, buf


def handle_message(idx, mtype, body, nodes):
    """Returns True if a valid CONNECT was decoded and stored."""
    if mtype == MSG_CONNECT:
        if len(body) != 6:
            print("node %s: bad CONNECT length %d" % (chr(65 + idx), len(body)))
            return False
        ip = socket.inet_ntoa(body[:4])           # 4 raw bytes -> "10.0.0.1"
        (port,) = struct.unpack('!H', body[4:6])  # 2 bytes, big-endian -> int
        nodes[idx] = (ip, port)
        print("CONNECT from %s = %s:%d" % (chr(65 + idx), ip, port))
        return True
    print("node %s: unknown message type %d" % (chr(65 + idx), mtype))
    return False


# ---- step 7: LINK-STATE ----

def pack_tuple(nodes, j, cost):
    ip, port = nodes[j]
    return TUP.pack(socket.inet_aton(ip), port, j, cost)


def build_link_state(idx, graph, nodes):
    """Full LINK-STATE message for node idx: its own tuple (cost 0) + one per neighbour."""
    n = len(graph)
    body = pack_tuple(nodes, idx, 0)
    if idx < n:                                   # idx >= n is an island: only its own tuple
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
        print("sent LINK-STATE to %s (%d bytes)" % (chr(65 + idx), len(msg)))
    except OSError as e:
        print("send to %s failed: %s" % (chr(65 + idx), e))


def broadcast(conns, graph, nodes):
    for idx in range(len(conns)):
        send_link_state(conns, idx, graph, nodes)


def main():
    # step 1
    if len(sys.argv) != 2:
        print("usage: python3 oracle_node.py <config_file>")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print("config file not found:", path)
        sys.exit(1)

    # step 2
    graph = read_config(path)
    n = len(graph)
    print("loaded config: %d nodes" % n)

    # step 3: listen for VN connections on TCP 5000
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PORT))
    srv.listen(32)
    print("listening on TCP port %d" % PORT)

    conns = []    # conns[0] = A, conns[1] = B, ...; None = disconnected
    bufs = []     # bufs[i] = bytes from conns[i] not yet parsed
    nodes = []    # nodes[i] = (ip, udp_port) once conns[i] sent CONNECT, else None
    started = False                   # step 9: True once all N nodes have sent CONNECT
    mtime = os.stat(path).st_mtime    # step 4: last-modified time we've seen

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
                    # step 5: accumulate bytes, parse complete messages
                    bufs[idx] += data
                    msgs, bufs[idx] = extract_messages(bufs[idx])
                    for mtype, body in msgs:
                        # step 6: decode CONNECT
                        if handle_message(idx, mtype, body, nodes):
                            # step 9: when to send LINK-STATE
                            if started:
                                send_link_state(conns, idx, graph, nodes)   # late joiner / island
                            elif len(nodes) >= n and all(x is not None for x in nodes[:n]):
                                started = True
                                broadcast(conns, graph, nodes)              # all N connected

        # step 4: check whether the config file changed
        try:
            new_mtime = os.stat(path).st_mtime
        except OSError:
            new_mtime = mtime         # file briefly missing (editor saving), skip this round

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
                        broadcast(conns, graph, nodes)    # step 9: re-send after every change


if __name__ == '__main__':
    main()