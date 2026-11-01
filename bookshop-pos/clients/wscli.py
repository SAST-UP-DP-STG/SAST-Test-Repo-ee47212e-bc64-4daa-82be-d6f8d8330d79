import sys

import simple_websocket


def main():
    if len(sys.argv) < 3:
        print('usage: python clients/wscli.py <ws-url> \'{"type":"..."}\' [...]')
        return
    url = sys.argv[1]
    messages = sys.argv[2:]
    client = simple_websocket.Client(url)
    try:
        for message in messages:
            client.send(message)
            print(client.receive())
    finally:
        client.close()


if __name__ == "__main__":
    main()
