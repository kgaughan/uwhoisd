"""
A 'universal' WHOIS proxy server.
"""

import asyncio
import configparser
import logging
import logging.config
import os.path
import re
import socket
import sys

from . import caching, client, server, utils

USAGE = "Usage: %s <config>"

PORT = socket.getservbyname("whois", "tcp")

logger = logging.getLogger("uwhoisd")


class UWhois:
    """
    Universal WHOIS proxy.
    """

    __slots__ = (
        "conservative",
        "overrides",
        "prefixes",
        "recursion_patterns",
        "registry_whois",
        "page_feed",
        "suffix",
    )

    def __init__(self):
        """
        Initialise the proxy.
        """
        super().__init__()
        self.suffix = None
        self.overrides = {}
        self.prefixes = {}
        self.recursion_patterns = {}
        self.registry_whois = False
        self.page_feed = True
        self.conservative = ()

    def read_config(self, parser):
        """
        Read the configuration for this object from a config file.
        """
        self.registry_whois = parser.get_bool("uwhoisd", "registry_whois")
        self.page_feed = parser.get_bool("uwhoisd", "page_feed")
        self.suffix = parser.get("uwhoisd", "suffix")
        self.conservative = parser.get_list("uwhoisd", "conservative")

        for section in ("overrides", "prefixes"):
            setattr(self, section, parser.get_section_dict(section))

        for zone, pattern in parser.items("recursion_patterns"):
            self.recursion_patterns[zone] = re.compile(utils.decode_value(pattern), re.I)

    def get_whois_server(self, zone):
        """
        Get the WHOIS server for the given zone.
        """
        if zone in self.overrides:
            server = self.overrides[zone]
        else:
            server = f"{zone}.{self.suffix}"
        if ":" in server:
            server, port = server.split(":", 1)
            port = int(port)
        else:
            port = PORT
        return server, port

    def get_registrar_whois_server(self, zone, response):
        """
        Extract the registrar's WHOIS server from the registry response.
        """
        matches = self.recursion_patterns[zone].search(response)
        return None if matches is None else matches.group("server")

    def get_prefix(self, zone):
        """
        Get the prefix required when querying the servers for the given zone.
        """
        return self.prefixes[zone] if zone in self.prefixes else ""

    async def whois(self, query: str) -> str:
        """
        Query the appropriate WHOIS server.
        """
        # Figure out the zone whose WHOIS server we're meant to be querying.
        for zone in self.conservative:
            if query.endswith(f".{zone}"):
                break
        else:
            _, zone = utils.split_fqdn(query)

        # Query the registry's WHOIS server.
        server, port = self.get_whois_server(zone)
        logger.info("Querying %s about %s", server, query)
        response = await client.query_whois(server, port, self.get_prefix(zone) + query)

        # Thin registry? Query the registrar's WHOIS server.
        if zone in self.recursion_patterns:
            server = self.get_registrar_whois_server(zone, response)
            if server is not None:
                if not self.registry_whois:
                    response = ""
                elif self.page_feed:
                    # A form feed character so it's possible to find the split.
                    response += "\f"
                logger.info("Recursive query to %s about %s", server, query)
                response += await client.query_whois(server, port, query)

        return response


def main():
    """
    Execute the daemon.
    """
    if len(sys.argv) != 2:
        print(USAGE % os.path.basename(sys.argv[0]), file=sys.stderr)
        return 1

    logging.config.fileConfig(sys.argv[1])

    try:
        logger.info("Reading config file at '%s'", sys.argv[1])
        parser = utils.make_config_parser(sys.argv[1])

        iface = parser.get("uwhoisd", "iface")
        port = parser.getint("uwhoisd", "port")
        logger.info("Listen on %s:%d", iface, port)

        uwhois = UWhois()
        uwhois.read_config(parser)

        cache = caching.get_cache(dict(parser.items("cache")))
        whois = caching.wrap_whois(cache, uwhois.whois)
    except configparser.Error:
        logger.exception("Could not parse config file")
        return 1
    else:
        asyncio.run(server.start_service(iface, port, whois))
        return 0


if __name__ == "__main__":
    sys.exit(main())
