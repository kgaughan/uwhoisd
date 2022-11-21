"""
Networking code.
"""

import logging
import signal
import socket

import tornado
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer

from . import utils


logger = logging.getLogger("uwhoisd")


def handle_signal(sig, frame):
    """
    Stop the main loop on signal.
    """
    IOLoop.instance().add_callback(IOLoop.instance().stop)


class WhoisClient(object):
    """
    Whois client.
    """

    def __init__(self, server, port):
        """
        A WHOIS client for Tornado.

        :param server string: hostname of downstream server.
        :param port int: port on downstream server to connect to.
        """
        self.server = server
        self.port = port

    def __enter__(self):
        """
        Initialize a `with` statement.
        """
        self.sock = socket.create_connection((self.server, self.port))
        self.sock.settimeout(10)
        return self

    def __exit__(self, type, value, traceback):
        """
        Terminate a `with` statement.
        """
        self.sock.close()

    def whois(self, query):
        """
        Perform a query against the server.
        """
        to_return = ""
        try:
            bytes_whois = b""
            self.sock.sendall("{0}\r\n".format(query).encode())
            while True:
                if data := self.sock.recv(2048):
                    bytes_whois += data
                    continue
                break
            to_return = str(bytes_whois, "utf-8", "ignore")
        except OSError as e:
            # Catches all socket.* exceptions
            return "{0}: {1}\n".format(self.server, e)
        except Exception:
            logger.exception("Unknown exception when querying '%s'", query)
        return to_return


class WhoisListener(TCPServer):
    """
    Listener for whois clients.
    """

    def __init__(self, whois):
        """
        Listen to queries from whois clients.
        """
        super(WhoisListener, self).__init__()
        self.whois = whois

    @gen.coroutine
    def handle_stream(self, stream, address):
        """
        Respond to a single request.
        """
        self.stream = stream
        try:
            whois_query = yield self.stream.read_until_regex(b"\n")
            whois_query = whois_query.decode().strip().lower()
            whois_entry = (
                self.whois(whois_query)
                if utils.is_well_formed_fqdn(whois_query)
                else "; Bad request: '{0}'\r\n".format(whois_query)
            )

            yield self.stream.write(whois_entry.encode())
        except tornado.iostream.StreamClosedError:
            logger.warning("Connection closed by %s.", address)
        except Exception:
            logger.exception("Unknown exception by '%s'", address)
        self.stream.close()


def start_service(iface, port, whois):
    """
    Start the service.
    """
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    server = WhoisListener(whois)
    logger.info("Listen on %s:%d", iface, port)
    server.bind(port, iface)
    server.start(None)
    IOLoop.instance().start()
    IOLoop.instance().close()
