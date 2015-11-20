"""
Networking code.
"""

import functools
import logging

import diesel

from uwhoisd import utils


CRLF = "\r\n"

logger = logging.getLogger('uwhoisd')


class Timeout(Exception):
    """
    Request to downstream server timed out.
    """

    __slots__ = ('server',)

    def __init__(self, server):
        super(Timeout, self).__init__()
        self.server = server


class WhoisClient(diesel.Client):
    """
    A WHOIS client for diesel.
    """

    __slots__ = ()

    @diesel.call
    def whois(self, query):
        """
        Perform a query against the server. Either returns the server's
        response or raises a `Timeout` exception if the downstream server
        took too long.
        """
        diesel.send(query + CRLF)
        result = []
        try:
            while True:
                evt, data = diesel.first(sleep=5, receive=2048)
                if evt == 'sleep':
                    raise Timeout(self.addr)
                result.append(data)
        except diesel.ConnectionClosed as ex:
            if ex.buffer:
                result.append(ex.buffer)
        return ''.join(result)


def respond(whois, addr):
    """
    Respond to a single request.
    """
    query = diesel.until_eol().rstrip(CRLF).lower()
    if not utils.is_well_formed_fqdn(query):
        diesel.send("; Bad request: '%s'\r\n" % query)
        return

    try:
        diesel.send(whois(query))
    except diesel.ClientConnectionError:
        logger.info("Connection refused")
        diesel.send("; Connection refused by downstream server\r\n")
    except diesel.ConnectionClosed:
        logger.info("Connection closed by %s", addr)
    except Timeout as ex:
        logger.info("Slow response")
        diesel.send("; Slow response from %s.\r\n" % ex.server)
    except diesel.DNSResolutionError as ex:
        logger.error("%s", ex.message)
        diesel.send("; %s\n\n" % ex.message)


def start_service(iface, port, whois):
    """
    Start the service.
    """
    diesel.quickstart(
        diesel.Service(functools.partial(respond, whois), port, iface))
