"""A 'universal' WHOIS proxy server."""

import asyncio
import configparser
import contextlib
import logging
import logging.config
import os.path
import re
import socket
import sys
import typing as t

from . import caching, client, server, utils

USAGE = "Usage: %s <config>"

PORT = socket.getservbyname("whois", "tcp")

logger = logging.getLogger(__name__)


class UWhois:
    """Universal WHOIS proxy."""

    __slots__ = (
        "conservative",
        "overrides",
        "page_feed",
        "prefixes",
        "recursion_patterns",
        "registry_whois",
        "suffix",
    )

    def __init__(self) -> None:
        super().__init__()
        self.suffix: t.Optional[str] = None
        self.overrides: dict[str, str] = {}
        self.prefixes: dict[str, str] = {}
        self.recursion_patterns: dict[str, re.Pattern] = {}
        self.registry_whois: bool = False
        self.page_feed: bool = True
        self.conservative: t.Sequence[str] = ()

    def read_config(self, parser: utils.ConfigParser) -> None:
        """Read the configuration for this object from a config file.

        Args:
            parser: The config parser to read from.
        """
        self.registry_whois = parser.get_bool("uwhoisd", "registry_whois")
        self.page_feed = parser.get_bool("uwhoisd", "page_feed")
        self.suffix = parser.get("uwhoisd", "suffix")
        self.conservative = parser.get_list("uwhoisd", "conservative")

        for section in ("overrides", "prefixes"):
            setattr(self, section, parser.get_section_dict(section))

        for zone, pattern in parser.items("recursion_patterns"):
            self.recursion_patterns[zone] = re.compile(utils.decode_value(pattern), re.IGNORECASE)

    def get_whois_server(self, zone: str) -> tuple[str, int]:
        """Get the WHOIS server for the given zone.

        Args:
            zone: The zone to get the WHOIS server for.

        Returns:
            A tuple of the WHOIS server and port.
        """
        server = self.overrides.get(zone, f"{zone}.{self.suffix}")
        if ":" in server:
            server, port = server.split(":", 1)
            return server, int(port)
        return server, PORT

    def get_registrar_whois_server(self, zone: str, response: str) -> t.Optional[str]:
        """Extract the registrar's WHOIS server from the registry response.

        Args:
            zone: The zone being queried.
            response: The response from the registry's WHOIS server.

        Returns:
            The registrar's WHOIS server, or None if not found.
        """
        matches = self.recursion_patterns[zone].search(response)
        return None if matches is None else matches.group("server")

    def get_prefix(self, zone: str) -> str:
        """Get the prefix required when querying the servers for the given zone.

        Args:
            zone: The zone to get the prefix for.

        Returns:
            The prefix string.
        """
        return self.prefixes.get(zone, "")

    async def whois(self, query: str) -> str:
        """Query the appropriate WHOIS server.

        Args:
            query: The WHOIS query.

        Returns:
            The WHOIS response.
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
            registrar_server = self.get_registrar_whois_server(zone, response)
            if registrar_server is not None:
                if not self.registry_whois:
                    response = ""
                elif self.page_feed:
                    # A form feed character so it's possible to find the split.
                    response += "\f"
                logger.info("Recursive query to %s about %s", registrar_server, query)
                response += await client.query_whois(registrar_server, port, query)

        return response


def main() -> int:
    """Execute the daemon."""
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
    with contextlib.suppress(KeyboardInterrupt):
        sys.exit(main())
