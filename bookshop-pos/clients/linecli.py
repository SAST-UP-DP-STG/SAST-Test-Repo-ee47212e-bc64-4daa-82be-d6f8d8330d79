import socket
import sys


def main():
    if len(sys.argv) < 3:
        print('usage: python clients/linecli.py <port> "LINE" ["LINE" ...]')
        return
    port = int(sys.argv[1])
    lines = sys.argv[2:]
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        stream = sock.makefile("rwb")
        for line in lines:
            stream.write((line + "\n").encode("utf-8"))
            stream.flush()
            reply = stream.readline()
            print(reply.decode("utf-8", "replace").rstrip())


if __name__ == "__main__":
    main()
