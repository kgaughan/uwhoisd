"""
A scraper which pulls zone WHOIS servers from IANA's root zone database.
"""

import logging
import socket
import sys
import time
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from bs4 import BeautifulSoup
import requests


ROOT_ZONE_DB = 'http://www.iana.org/domains/root/db'


def fetch(url):
    """
    Fetch a URL and parse it with Beautiful Soup for scraping.
    """
    return BeautifulSoup(requests.get(url).text, 'html.parser')


def scrape_whois_from_iana(root_zone_db_url):
    """
    Scrape IANA's root zone database for WHOIS servers.
    """
    logging.info("Scraping %s", root_zone_db_url)
    body = fetch(root_zone_db_url)

    for link in body.select('#tld-table .tld a'):
        if 'href' not in link.attrs:
            continue

        # Is this a zone we should skip/ignore?
        row = link.parent.parent.parent.findChildren('td')
        if row[1].string == 'test':
            continue
        if row[2].string in ('Not assigned', 'Retired'):
            continue

        zone_url = urljoin(root_zone_db_url, link.attrs['href'])
        logging.info("Scraping %s", zone_url)
        body = fetch(zone_url)

        title = body.find('h1')
        if title is None:
            logging.info("No title found")
            continue
        title_parts = ''.join(title.strings).split('.', 1)
        if len(title_parts) != 2:
            logging.info("Could not find TLD in '%s'", title)
            continue
        ace_zone = title_parts[1].encode('idna').decode().lower()

        whois_server_label = body.find('b', text='WHOIS Server:')
        whois_server = ''
        if whois_server_label is not None:
            whois_server = whois_server_label.next_sibling.strip().lower()

        # Fallback to trying whois.nic.*
        if whois_server == '':
            whois_server = 'whois.nic.%s' % ace_zone
            logging.info("Trying fallback server: %s", whois_server)
            try:
                socket.gethostbyname(whois_server)
            except socket.gaierror:
                whois_server = ''

        if whois_server == '':
            logging.info("No WHOIS server found for %s", ace_zone)
        else:
            logging.info("WHOIS server for %s is %s", ace_zone, whois_server)
            yield (ace_zone, whois_server)


def main():
    """
    Driver for scraper.
    """
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    print('[overrides]')
    for ace_zone, whois_server in scrape_whois_from_iana(ROOT_ZONE_DB):
        print('%s=%s' % (ace_zone, whois_server))
    logging.info("Done")
    return 0


if __name__ == '__main__':
    sys.exit(main())
