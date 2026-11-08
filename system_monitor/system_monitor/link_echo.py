#!/usr/bin/env python3
"""Echo server for the link probes, run on the remote side: returns them with a receive time."""
import argparse
import socket
import struct
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', args.port))
    while True:
        data, addr = sock.recvfrom(64)
        sock.sendto(data + struct.pack('<Q', time.time_ns()), addr)


if __name__ == '__main__':
    main()
