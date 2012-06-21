"""
"""

import socket


def create_server_socket(addr, port, backlog=5, reuse_addr=True):
    sock = socket.socket()
    if reuse_addr:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((addr, port))
    sock.listen(backlog)
    return sock


def main():
    server = create_server_socket('0.0.0.0', 1043, reuse_addr=True)
    while True:
        client, (addr, port) = server.accept()
        print addr, port
        request = ''
        while True:
            received = client.recv(4096)
            i = received.find('\r\n')
            if i == -1:
                request += received
            else:
                request += received[:i]
                break
        client.sendall("You sent: [-%s-]\nFun!\n" % request)
        client.close()


if __name__ == '__main__':
    main()
