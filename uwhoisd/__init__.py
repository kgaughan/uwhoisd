"""
A 'universal' WHOIS proxy server.
"""

from ConfigParser import SafeConfigParser
import logging
import logging.config
import os.path
import re
import socket
import sys

from uwhoisd import utils, net


__version__ = '0.0.5'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


USAGE = "Usage: %s <config>"

PORT = socket.getservbyname('whois', 'tcp')

logger = logging.getLogger('uwhoisd')


class UWhois(object):
    """
    Universal WHOIS proxy.
    """

    __slots__ = (
        'suffix', 'overrides', 'prefixes', 'recursion_patterns',
        'conservative', 'registry_whois')

    def __init__(self):
        super(UWhois, self).__init__()
        self.suffix = None
        self.overrides = {}
        self.prefixes = {}
        self.recursion_patterns = {}
        self.registry_whois = False
        self.conservative = ()

    def _get_dict(self, parser, section):
        """
        Pull a dictionary out of the config safely.
        """
        if parser.has_section(section):
            values = dict(
                (key, utils.decode_value(value))
                for key, value in parser.items(section))
        else:
            values = {}
        setattr(self, section, values)

    def read_config(self, parser):
        """
        Read the configuration for this object from a config file.
        """
        self.registry_whois = utils.to_bool(
            parser.get('uwhoisd', 'registry_whois'))
        self.suffix = parser.get('uwhoisd', 'suffix')
        self.conservative = [
            zone
            for zone in parser.get('uwhoisd', 'conservative').split("\n")
            if zone != '']

        for section in ('overrides', 'prefixes'):
            self._get_dict(parser, section)

        for zone, server in self.overrides.iteritems():
            if not utils.is_well_formed_fqdn(server):
                raise Exception(
                    "Bad server for zone %s in overrides: %s" % (zone, server))

        for zone, pattern in parser.items('recursion_patterns'):
            self.recursion_patterns[zone] = re.compile(
                utils.decode_value(pattern),
                re.I)

    def get_whois_server(self, zone):
        """
        Get the WHOIS server for the given zone.
        """
        if zone in self.overrides:
            return self.overrides[zone]
        return zone + '.' + self.suffix

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
        """
        Query the appropriate WHOIS server.
        """
        # Figure out the zone whose WHOIS server we're meant to be querying.
        for zone in self.conservative:
            if query.endswith('.' + zone):
                break
        else:
            _, zone = utils.split_fqdn(query)

        # Query the registry's WHOIS server.
        server = self.get_whois_server(zone)
        with net.WhoisClient(server, PORT) as client:
            logger.info("Querying %s about %s", server, query)
            response = client.whois(self.get_prefix(zone) + query)

        # Thin registry? Query the registrar's WHOIS server.
        if zone in self.recursion_patterns:
            server = self.get_registrar_whois_server(zone, response)
            if server is not None:
                if not self.registry_whois:
                    response = ""
                with net.WhoisClient(server, PORT) as client:
                    logger.info(
                        "Recursive query to %s about %s",
                        server, query)
                    response += client.whois(query)

        return response


def make_default_config_parser():
    """
    Creates a config parser with the bare minimum of defaults.
    """
    defaults = {
        'iface': '0.0.0.0',
        'port': str(PORT),
        'registry_whois': 'false',
        'suffix': 'whois-servers.net'}

    parser = SafeConfigParser()
    # Sections that need to at least be present, even if they're empty.
    for section in ('uwhoisd', 'overrides', 'prefixes', 'recursion_patterns'):
        parser.add_section(section)
    for key, value in defaults.iteritems():
        parser.set('uwhoisd', key, value)

    return parser


def main():
    """
    Execute the daemon.
    """
    if len(sys.argv) != 2:
        print >> sys.stderr, USAGE % os.path.basename(sys.argv[0])
        return 1

    logging.config.fileConfig(sys.argv[1])

    parser = make_default_config_parser()

    try:
        logger.info("Reading config file at '%s'", sys.argv[1])
        parser.read(sys.argv[1])

        iface = parser.get('uwhoisd', 'iface')
        port = parser.getint('uwhoisd', 'port')
        logger.info("Listen on %s:%d", iface, port)

        uwhois = UWhois()
        uwhois.read_config(parser)

        if parser.has_section('cache'):
            logger.info("Caching activated")
            cache = utils.Cache(
                max_size=parser.getint('cache', 'max_size'),
                max_age=parser.getint('cache', 'max_age'))

            def whois(query):
                """Caching wrapper around UWhois."""
                cache.evict_expired()
                if query in cache:
                    logger.info("Cache hit for %s", query)
                    response = cache[query]
                else:
                    response = uwhois.whois(query)
                    cache[query] = response
                return response
        else:
            logger.info("Caching deactivated")
            whois = uwhois.whois
    except Exception, ex:  # pylint: disable-msg=W0703
        print >> sys.stderr, "Could not parse config file: %s" % str(ex)
        return 1

    net.start_service(iface, port, whois)
    return 0


if __name__ == '__main__':
    sys.exit(main())
