"""
A scraper which pulls zone WHOIS servers from IANA's root zone database.
"""

import argparse
import logging
import socket
import sys
from urllib.parse import urljoin
import xml.etree.ElementTree as etree

from bs4 import BeautifulSoup
import requests

from . import utils


IPV4_ASSIGNMENTS = (
    "http://www.iana.org/assignments/ipv4-address-space/ipv4-address-space.xml"
)  # noqa: E501
ROOT_ZONE_DB = "http://www.iana.org/domains/root/db"

NSS = {"assignments": "http://www.iana.org/assignments"}


def fetch_ipv4_assignments(url):
    """
    Fetch WHOIS server list for the IPv4 /8 assignments from IANA.
    """
    res = requests.get(url, stream=False)
    root = etree.fromstring(res.text)
    for record in root.findall("assignments:record", NSS):
        status = record.find("assignments:status", NSS).text
        if status not in ("ALLOCATED", "LEGACY"):
            continue
        prefix = record.find("assignments:prefix", NSS).text
        prefix, _ = prefix.lstrip("0").split("/", 1)
        whois = record.find("assignments:whois", NSS).text
        yield prefix, whois


def fetch(session, url):
    """
    Fetch a URL and parse it with Beautiful Soup for scraping.
    """
    return BeautifulSoup(requests.get(url, stream=False).text, "html.parser")


def munge_zone(zone):
    """
    Beat the zone text into an a-label.
    """
    # The .strip() here is needed for RTL scripts like Arabic.
    return zone.strip("\u200E\u200F.").encode("idna").decode().lower()


def scrape_whois_from_iana(root_zone_db_url, existing):
    """
    Scrape IANA's root zone database for WHOIS servers.
    """
    session = requests.Session()

    logging.info("Scraping %s", root_zone_db_url)
    body = fetch(session, root_zone_db_url)

    for link in body.select("#tld-table .tld a"):
        if "href" not in link.attrs:
            continue

        zone = munge_zone(link.string)
        # If we've already scraped this TLD, ignore it.
        if zone in existing:
            continue

        # Is this a zone we should skip/ignore?
        row = link.parent.parent.parent.findChildren("td")
        if row[1].string == "test":
            continue
        if row[2].string in ("Not assigned", "Retired"):
            continue

        zone_url = urljoin(root_zone_db_url, link.attrs["href"])
        logging.info("Scraping %s", zone_url)
        body = fetch(session, zone_url)

        whois_server_label = body.find("b", text="WHOIS Server:")
        whois_server = ""
        if whois_server_label is not None:
            whois_server = whois_server_label.next_sibling.strip().lower()

        # Fallback to trying whois.nic.*
        if whois_server == "":
            whois_server = "whois.nic.%s" % zone
            logging.info("Trying fallback server: %s", whois_server)
            try:
                socket.gethostbyname(whois_server)
            except socket.gaierror:
                whois_server = ""

        if whois_server == "":
            logging.info("No WHOIS server found for %s", zone)
        else:
            logging.info("WHOIS server for %s is %s", zone, whois_server)
            yield (zone, whois_server)


def make_arg_parser():
    """
    Create the argument parser.
    """
    parser = argparse.ArgumentParser(description="Scrap WHOIS data.")
    parser.add_argument("--config", help="uwhoisd configuration")
    parser.add_argument(
        "--log",
        default="warning",
        choices=["critical", "error", "warning", "info", "debug"],
        help="Logging level",
    )
    parser.add_argument("--ipv4", action="store_true", help="Scrape IPv4 assignments")
    zone_group = parser.add_mutually_exclusive_group(required=True)
    zone_group.add_argument(
        "--new-only",
        action="store_true",
        help="Only scrape new zones (requires config)",
    )
    zone_group.add_argument("--full", action="store_true", help="Do a full zone scrape")
    return parser


def main():
    """
    Driver for scraper.
    """
    args = make_arg_parser().parse_args()

    logging.basicConfig(stream=sys.stderr, level=logging.getLevelName(args.log.upper()))

    parser = utils.make_config_parser(args.config)

    whois_servers = {} if args.full else parser.get_section_dict("overrides")
    for zone, whois_server in scrape_whois_from_iana(ROOT_ZONE_DB, whois_servers):
        whois_servers[zone] = whois_server
    print("[overrides]")
    for zone in sorted(whois_servers):
        print("%s=%s" % (zone, whois_servers[zone]))

    if args.ipv4:
        print("[ipv4_assignments]")
        for prefix, whois_server in fetch_ipv4_assignments(IPV4_ASSIGNMENTS):
            print("%s=%s" % (prefix, whois_server))

    logging.info("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
