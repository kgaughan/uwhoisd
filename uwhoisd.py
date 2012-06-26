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
ZONE_PATTERN = re.compile('^([-a-z0-9]+)(\.[-a-z0-9]+)?$')

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


def ensure_sections_present(parser, sections):
    """Ensure all sections are present, even if empty."""
    for section in sections:
        if not parser.has_section(section):
            parser.add_section(section)


def validate_overrides(overrides):
    """Ensure all the override entries in the config file are good."""
    for zone, server in overrides.iteritems():
        if ZONE_PATTERN.match(zone) is None:
            raise Exception(
                "Bad zone in overrides: %s" % zone)
        if FQDN_PATTERN.match(server) is None:
            raise Exception(
                "Bad server for zone %s in overrides: %s" % (zone, server))
        if len(socket.getaddrinfo(server, None)) == 0:
            raise Exception("The name '%s' does not resolve." % server)


def validate_prefixes(prefixes):
    """Ensure prefixes are good."""
    for zone in prefixes:
        if ZONE_PATTERN.match(zone) is None:
            raise Exception(
                "Bad zone in prefixes: %s" % zone)


def read_config(parser):
    """
    Extract the configuration from a parsed configuration file, checking that
    the data contained within is valid.
    """
    def safe_get(section, option, default):
        """Get a configuration option safely."""
        if parser.has_option(section, option):
            return parser.get(section, option)
        return default

    iface = safe_get('uwhoisd', 'iface', '0.0.0.0')
    port = int(safe_get('uwhoisd', 'port', PORT))
    suffix = safe_get('uwhoisd', 'suffix', 'whois-servers.net')
    if FQDN_PATTERN.match(suffix) is None:
        raise Exception("Malformed suffix: %s" % suffix)

    overrides = dict(parser.items('overrides'))
    prefixes = dict(parser.items('prefixes'))
    validate_overrides(overrides)
    validate_prefixes(prefixes)

    recursion_patterns = {}
    for zone, pattern in parser.items('recursion_patterns'):
        if ZONE_PATTERN.match(zone) is None:
            raise Exception(
                "Bad zone in recursion_patterns: %s" % zone)
        recursion_patterns[zone] = re.compile(pattern)

    return (iface, port, suffix, overrides, prefixes, recursion_patterns)


class UWhois(object):
    """Universal WHOIS proxy."""

    __slots__ = ('suffix', 'overrides', 'prefixes', 'recursion_patterns')

    def __init__(self, suffix, overrides, prefixes, recursion_patterns):
        super(UWhois, self).__init__()
        self.suffix = suffix
        self.overrides = overrides
        self.prefixes = prefixes
        self.recursion_patterns = recursion_patterns

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

    def whois(self, query, zone):
        """Query the appropriate WHOIS server."""
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


class CachingUWhois(UWhois):
    """Caching variant of `UWhois`."""

    __slots__ = ('cache',)

    def __init__(self, suffix, overrides, prefixes, recursion_patterns):
        super(CachingUWhois, self).__init__(
            suffix, overrides, prefixes, recursion_patterns)
        self.cache = Cache()

    def whois(self, query, zone):
        self.cache.evict_expired()
        if query in self.cache:
            response = self.cache[query]
        else:
            response = super(CachingUWhois, self).whois(query, zone)
            self.cache[query] = response
        return response


def respond(uwhois, _addr):
    """Respond to a single request."""
    query = diesel.until_eol().rstrip(CRLF).lower()
    if FQDN_PATTERN.match(query) is None:
        diesel.send("; Bad request: '%s'\r\n" % query)
        return

    _, zone = split_fqdn(query)

    try:
        diesel.send(uwhois.whois(query, zone))
    except Timeout, ex:
        diesel.send("; Slow response from %s.\r\n" % ex.server)


def main():
    """Execute the daemon."""
    if len(sys.argv) != 2:
        print >> sys.stderr, USAGE % os.path.basename(sys.argv[0])
        return 1

    parser = SafeConfigParser(allow_no_value=True)
    parser.read(sys.argv[1])
    ensure_sections_present(
        parser, ('uwhoisd', 'overrides', 'prefixes', 'recursion_patterns'))
    try:
        iface, port, suffix, overrides, prefixes, recursion_patterns = \
            read_config(parser)
    except Exception, ex:
        print >> sys.stderr, "Could not parse config file: %s" % str(ex)
        return 1

    uwhois = CachingUWhois(suffix, overrides, prefixes, recursion_patterns)
    service = diesel.Service(functools.partial(respond, uwhois), port, iface)
    diesel.quickstart(service)
    return 0


if __name__ == '__main__':
    sys.exit(main())
