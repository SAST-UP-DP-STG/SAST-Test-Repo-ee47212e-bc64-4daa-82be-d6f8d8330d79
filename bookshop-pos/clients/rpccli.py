import sys
import xmlrpc.client


class _TokenTransport(xmlrpc.client.Transport):
    def __init__(self, token):
        super().__init__()
        self._token = token

    def get_host_info(self, host):
        host, extra_headers, x509 = super().get_host_info(host)
        extra_headers = extra_headers or []
        extra_headers.append(("Authorization", "Bearer " + self._token))
        return host, extra_headers, x509


def _coerce(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def main():
    args = sys.argv[1:]
    token = None
    if "--token" in args:
        index = args.index("--token")
        token = args[index + 1]
        del args[index : index + 2]
    if not args:
        print("usage: python clients/rpccli.py <method> [args...] [--token TOKEN]")
        return
    method = args[0]
    params = [_coerce(a) for a in args[1:]]
    transport = _TokenTransport(token) if token else None
    proxy = xmlrpc.client.ServerProxy(
        "http://127.0.0.1:9130/RPC2", transport=transport, allow_none=True
    )
    print(getattr(proxy, method)(*params))


if __name__ == "__main__":
    main()
