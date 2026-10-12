import os
import select
import socket
import struct
import sys

from config_parser import read_config

PORT = 5000
POLL_SECS = 1.0

HDR = struct.Struct('!BH')


def extract_messages(buf):
    msgs = []
    while len(buf) >= HDR.size:
        mtype, blen = HDR.unpack_from(buf)
        if len(buf) < HDR.size + blen:
            break                      
        msgs.append((mtype, buf[HDR.size:HDR.size + blen]))
        buf = buf[HDR.size + blen:]
    return msgs, buf


def handle_message(idx, mtype, body):
    print("node %s: message type %d, %d byte body" % (chr(65 + idx), mtype, len(body)))


def main():
    if len(sys.argv) < 2:
        print("usage: oracle_node.py <config>")
        sys.exit(1)

    path = sys.argv[1]
    graph = read_config(path)
    n = len(graph)
    print("loaded config: %d nodes" % n)

    # step 3: listen for VN connections on TCP 5000

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PORT))    
    srv.listen(32)
    print("listening on TCP port %d" % PORT)

    conns = []
    bufs = []  
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
                else:
                    # step 5: accumulate bytes, parse complete app-layer messages
                    bufs[idx] += data
                    msgs, bufs[idx] = extract_messages(bufs[idx])
                    for mtype, body in msgs:
                        handle_message(idx, mtype, body)

        # step 4: poll config file for changes (runs every POLL_SECS)
        new_mtime = os.stat(path).st_mtime

        if new_mtime != mtime:
            mtime = new_mtime
            new_graph = read_config(path)
            if len(new_graph) != n:
                print("node count changed, ignoring")
                continue
            graph = new_graph
            print("config changed:")
            for row in graph:
                print(row)


if __name__ == '__main__':
    main()