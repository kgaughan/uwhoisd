"""
A scraper which pulls zone WHOIS servers from IANA's root zone database.
"""

import argparse
import logging
import socket
import sys
import typing as t
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import requests

from . import utils

IPV4_ASSIGNMENTS = "https://www.iana.org/assignments/ipv4-address-space/ipv4-address-space.xml"
ROOT_ZONE_DB = "https://www.iana.org/domains/root/db"

NSS = {"assignments": "http://www.iana.org/assignments"}

logging.basicConfig(level=logging.INFO, stream=sys.stderr)


def fetch_ipv4_assignments(url: str):
    """
    Fetch WHOIS server list for the IPv4 /8 assignments from IANA.
    """
    res = requests.get(url, stream=False, timeout=10)
    root = ET.fromstring(res.text)  # noqa: S314
    for record in root.findall("assignments:record", NSS):
        status = record.findtext("assignments:status", default="", namespaces=NSS)
        if status not in ("ALLOCATED", "LEGACY"):
            continue
        prefix = record.findtext("assignments:prefix", default="", namespaces=NSS)
        prefix, _ = prefix.lstrip("0").split("/", 1)
        whois = record.findtext("assignments:whois", default="", namespaces=NSS)
        if prefix != "" and whois != "":
            yield prefix, whois


def fetch(session: requests.Session, url: str) -> BeautifulSoup:
    """
    Fetch a URL and parse it with Beautiful Soup for scraping.
    """
    return BeautifulSoup(session.get(url, stream=False, timeout=10).text, "html.parser")


def munge_zone(zone: str) -> str:
    """
    Beat the zone text into an a-label.
    """
    # The .strip() here is needed for RTL scripts like Arabic.
    return zone.strip("\u200e\u200f.").encode("idna").decode().lower()


def scrape_whois_from_iana(root_zone_db_url: str, existing: t.Mapping[str, str]) -> t.Iterator[t.Tuple[str, str]]:
    """
    Scrape IANA's root zone database for WHOIS servers.
    """
    session = requests.Session()

    logging.info("Scraping %s", root_zone_db_url)
    body = fetch(session, root_zone_db_url)

    for zone, zone_url in extract_zone_urls(root_zone_db_url, body):
        # If we've already scraped this TLD, ignore it.
        if zone in existing:
            yield (zone, existing[zone])
            continue

        logging.info("Scraping %s", zone_url)
        body = fetch(session, zone_url)
        whois_server = extract_whois_server(body)
        # Fallback to trying whois.nic.*
        if whois_server is None:
            whois_server = f"whois.nic.{zone}"
            logging.info("Trying fallback server: %s", whois_server)
            try:
                socket.gethostbyname(whois_server)
            except socket.gaierror:
                logging.info("No WHOIS server found for %s", zone)
                continue

        logging.info("WHOIS server for %s is %s", zone, whois_server)
        yield (zone, whois_server)


def extract_zone_urls(base_url: str, body: BeautifulSoup) -> t.Iterator[t.Tuple[str, str]]:
    for link in body.select("#tld-table .tld a"):
        if "href" not in link.attrs or link.string is None:  # pragma: no cover
            continue
        row = link.find_parent("tr")
        if row is None:  # pragma: no cover
            continue
        tds = row.find_all("td")
        # Is this a zone we should skip/ignore?
        if tds[1].string == "test":
            continue
        if tds[2].string in ("Not assigned", "Retired"):
            continue

        yield (munge_zone(link.string), urljoin(base_url, link.attrs["href"]))


def extract_whois_server(body: BeautifulSoup) -> t.Optional[str]:
    whois_server_label = body.find("b", string="WHOIS Server:")
    if whois_server_label is None or whois_server_label.next_sibling is None:
        return None
    server = whois_server_label.next_sibling.text.strip().lower()
    return None if server == "" else server


def make_arg_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser.
    """
    parser = argparse.ArgumentParser(description="Scrap WHOIS data.")
    parser.add_argument("--config", help="uwhoisd configuration")
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

    parser = utils.make_config_parser(args.config)

    whois_servers = {} if args.full else parser.get_section_dict("overrides")
    logging.info("Starting scrape of %s", ROOT_ZONE_DB)
    print("[overrides]")
    for zone, whois_server in scrape_whois_from_iana(ROOT_ZONE_DB, whois_servers):
        logging.info("Scraped .%s: %s", zone, whois_server)
        print(f"{zone}={whois_server}")

    if args.ipv4:
        print("[ipv4_assignments]")
        for prefix, whois_server in fetch_ipv4_assignments(IPV4_ASSIGNMENTS):
            print(f"{prefix}={whois_server}")

    logging.info("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
