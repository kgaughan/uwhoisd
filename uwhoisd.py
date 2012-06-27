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
import time
import collections
import functools
from ConfigParser import SafeConfigParser


__version__ = '0.0.2'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


USAGE = "Usage: %s <config>"

PORT = socket.getservbyname('whois', 'tcp')

# We only accept ASCII or ACE-encoded domain names. IDNs must be converted
# to ACE first.
FQDN_PATTERN = re.compile('^([-a-z0-9]+)(\.[-a-z0-9]+){1,2}$')

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
    """Returns the WHOIS server hostname for a given zone."""
    return overrides[zone] if zone in overrides else zone + '.' + suffix


class Timeout(Exception):
    """Request to downstream server timed out."""

    __slots__ = ('server',)

    def __init__(self, server):
        super(Timeout, self).__init__()
        self.server = server


class WhoisClient(diesel.Client):
    """A WHOIS client for diesel."""

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


class Cache(object):
    """A simple LFU cache."""

    # This is implemented as an LFU cache. The eviction queue contains
    # 2-tuples consisting of the time the item was put into the cache and the
    # cache key. The cache maps cache keys onto 2-tuples consisting of a
    # counter giving the number of times this item occurs on the eviction queue
    # and the value.
    #
    # I may end up reimplementing this as an LRU cache if it turns out that's
    # more apt, but I haven't went that route as an LRU cache is somewhat more
    # awkward and involved to implement correctly.

    __slots__ = ('cache', 'queue', 'max_size', 'max_age', 'clock')

    def __init__(self, max_size=256, max_age=300, clock=time.time):
        self.cache = {}
        self.queue = collections.deque()
        self.max_size = max_size
        self.max_age = max_age
        self.clock = clock

    def evict_one(self):
        """Remove the item at the head of the eviction cache."""
        _, key = self.queue.popleft()
        self.attempt_eviction(key)

    def attempt_eviction(self, key):
        """Attempt to remove the named item from the cache"""
        counter, value = self.cache[key]
        counter -= 1
        if counter == 0:
            del self.cache[key]
        else:
            self.cache[key] = (counter, value)

    def evict_expired(self):
        """Evict any items older than the maximum age from the cache."""
        cutoff = self.clock() - self.max_age
        while len(self.queue) > 0:
            ts, key = self.queue.popleft()
            if ts > cutoff:
                self.queue.appendleft((ts, key))
                break
            self.attempt_eviction(key)

    def __len__(self):
        return len(self.cache)

    def __contains__(self, key):
        return key in self.cache

    def __getitem__(self, key):
        if key not in self.cache:
            raise IndexError
        _, value = self.cache[key]
        # Force this onto the top of the heap.
        self[key] = value
        return value

    def __setitem__(self, key, value):
        if len(self.queue) == self.max_size:
            self.evict_one()
        if key in self.cache:
            counter, _ = self.cache[key]
        else:
            counter = 0
        self.cache[key] = (counter + 1, value)
        self.queue.append((self.clock(), key))


class UWhois(object):
    """Universal WHOIS proxy."""

    __slots__ = ('suffix', 'overrides', 'prefixes', 'recursion_patterns')

    def __init__(self):
        super(UWhois, self).__init__()
        self.suffix = None
        self.overrides = {}
        self.prefixes = {}
        self.recursion_patterns = {}

    def _get_dict(self, parser, section):
        """Pull a dictionary out of the config safely."""
        if not parser.has_section(section):
            parser.add_section(section)
        setattr(self, section, dict(parser.items(section)))

    def read_config(self, parser):
        """Read the configuration for this object from a config file."""
        self.suffix = parser.get('uwhoisd', 'suffix')
        for section in ('overrides', 'prefixes'):
            self._get_dict(parser, section)

        for zone, server in self.overrides.iteritems():
            if FQDN_PATTERN.match(server) is None:
                raise Exception(
                    "Bad server for zone %s in overrides: %s" % (zone, server))

        for zone, pattern in parser.items('recursion_patterns'):
            self.recursion_patterns[zone] = re.compile(pattern)

    def get_whois_server(self, zone):
        """Get the WHOIS server for the given zone."""
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

    def whois(self, query):
        """Query the appropriate WHOIS server."""
        _, zone = split_fqdn(query)

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


def respond(whois, _addr):
    """Respond to a single request."""
    query = diesel.until_eol().rstrip(CRLF).lower()
    if FQDN_PATTERN.match(query) is None:
        diesel.send("; Bad request: '%s'\r\n" % query)
        return

    try:
        diesel.send(whois(query))
    except diesel.ClientConnectionError:
        diesel.send("; Connection refused by downstream server\r\n")
    except Timeout, ex:
        diesel.send("; Slow response from %s.\r\n" % ex.server)


def main():
    """Execute the daemon."""
    if len(sys.argv) != 2:
        print >> sys.stderr, USAGE % os.path.basename(sys.argv[0])
        return 1

    defaults = {
        'iface': '0.0.0.0',
        'port': str(PORT),
        'prefix': 'whois-servers.net'}

    parser = SafeConfigParser(allow_no_value=True)
    parser.add_section('uwhoisd')
    for key, value in defaults.iteritems():
        parser.set('uwhoisd', key, value)

    try:
        parser.read(sys.argv[1])

        iface = parser.get('uwhoisd', 'iface')
        port = parser.getint('uwhoisd', 'port')

        uwhois = UWhois()
        uwhois.read_config(parser)

        if parser.has_section('cache'):
            cache = Cache(
                max_size=parser.getint('cache', 'max_size'),
                max_age=parser.getint('cache', 'max_age'))

            def whois(query):
                """Caching wrapper around UWhois."""
                cache.evict_expired()
                if query in cache:
                    response = cache[query]
                else:
                    response = uwhois.whois(query)
                    cache[query] = response
                return response
        else:
            whois = uwhois.whois
    except Exception, ex:
        print >> sys.stderr, "Could not parse config file: %s" % str(ex)
        return 1

    service = diesel.Service(functools.partial(respond, whois), port, iface)
    diesel.quickstart(service)
    return 0


if __name__ == '__main__':
    sys.exit(main())
