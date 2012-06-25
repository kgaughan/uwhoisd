#
# uwhoisd
# by Keith Gaughan <http://stereochro.me/>
#
# Copyright (c) Keith Gaughan, 2012
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

"""
A 'universal' WHOIS proxy server.
"""

import diesel
import re
import os.path
import sys
import socket
from ConfigParser import SafeConfigParser


__version__ = '0.0.1'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


USAGE = "Usage: %s <config>"

PORT = socket.getservbyname('whois', 'tcp')

# We only accept ASCII or ACE-encoded domain names. IDNs must be converted
# to ACE first.
FQDN_PATTERN = re.compile('^([-a-z0-9]+)(\.[-a-z0-9]+){1,2}$', re.I)

CRLF = "\r\n"


def split_fqdn(fqdn):
    """
    Splits an FQDN into the domain name and zone.

    >>> split_fqdn('stereochro.me')
    ['stereochro', 'me']
    >>> split_fqdn('stereochro.me.')
    ['stereochro', 'me']
    >>> split_fqdn('stereochrome')
    ['stereochrome']
    >>> split_fqdn('keithgaughan.co.uk')
    ['keithgaughan', 'co.uk']
    """
    return fqdn.rstrip('.').split('.', 1)


def get_whois_server(suffix, overrides, zone):
    """
    Returns the WHOIS server hostname for a given zone.
    """
    return overrides[zone] if zone in overrides else zone + '.' + suffix


class Timeout(Exception):
    """Request to downstream server timed out."""

    __slots__ = ('server')

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
        except diesel.ConnectionClosed, ex:
            if ex.buffer:
                result.append(ex.buffer)
        return ''.join(result)


def read_config(parser):
    """
    Extract the configuration from a parsed configuration file, checking that
    the data contained within is valid.
    """
    # Ensure all sections are present, even if empty.
    for section in ('uwhoisd', 'overrides', 'prefixes', 'recursion_patterns'):
        if not parser.has_section(section):
            parser.add_section(section)

    def safe_get(section, option, default):
        """Get a configuration option safely."""
        if parser.has_option(section, option):
            return parser.get(section, option)
        return default

    iface = safe_get('uwhoisd', 'iface', '0.0.0.0')
    port = int(safe_get('uwhoisd', 'port', PORT))
    suffix = safe_get('uwhoisd', 'suffix', 'whois-servers.net')

    # TODO: Check all hostnames and zone names are well-formed.
    overrides = dict(parser.items('overrides'))
    prefixes = dict(parser.items('prefixes'))

    # We could use a compilation cache for these things, but the re module does
    # that anyway, so why bother.
    recursion_patterns = {}
    for zone, pattern in parser.items('recursion_patterns'):
        recursion_patterns[zone] = re.compile(pattern)

    return (iface, port, suffix, overrides, prefixes, recursion_patterns)


class Responder(object):
    """
    Responds to requests.
    """

    __slots__ = ('suffix', 'overrides', 'prefixes', 'recursion_patterns')

    def __init__(self, suffix, overrides, prefixes, recursion_patterns):
        super(Responder, self).__init__()
        self.suffix = suffix
        self.overrides = overrides
        self.prefixes = prefixes
        self.recursion_patterns = recursion_patterns

    def get_whois_server(self, zone):
        """
        Get the WHOIS server for the given zone.
        """
        return get_whois_server(self.suffix, self.overrides, zone)

    def get_registrar_whois_server(self, zone, response):
        """
        Extract the registrar's WHOIS server from the registry response.
        """
        matches = self.recursion_patterns[zone].search(response)
        return None if matches is None else matches.group('server')

    def get_prefix(self, zone):
        """
        Gets the prefix required when querying the servers for the given zone.
        """
        return self.prefixes[zone] if zone in self.prefixes else ''

    def whois(self, query, zone):
        """
        Query the appropriate WHOIS server.
        """
        # Query the registry's WHOIS server.
        with WhoisClient(self.get_whois_server(zone), PORT) as client:
            response = client.whois(self.get_prefix(zone) + query)

        # Thin registry? Query the registrar's WHOIS server.
        if zone in self.recursion_patterns:
            server = self.get_registrar_whois_server(zone, response)
            if server is not None:
                with WhoisClient(server, PORT) as client:
                    response = client.whois(query)

        return response

    def respond(self, _addr):
        """
        Respond to a single request.
        """
        query = diesel.until_eol().rstrip(CRLF).lower()
        if FQDN_PATTERN.match(query) is None:
            diesel.send("; Bad request: '%s'\r\n" % query)
            return

        _, zone = split_fqdn(query)

        try:
            diesel.send(self.whois(query, zone))
        except Timeout, ex:
            diesel.send("; Slow response from %s.\r\n" % ex.server)


def main():
    """
    Execute the daemon.
    """
    if len(sys.argv) != 2:
        print >> sys.stderr, USAGE % os.path.basename(sys.argv[0])
        return 1

    parser = SafeConfigParser(allow_no_value=True)
    parser.read(sys.argv[1])
    iface, port, suffix, overrides, prefixes, recursion_patterns = \
        read_config(parser)

    responder = Responder(suffix, overrides, prefixes, recursion_patterns)
    diesel.quickstart(diesel.Service(responder.respond, port, iface))


if __name__ == '__main__':
    main()
