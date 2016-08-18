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
SLEEP = 0


def main():
    """
    Scrape IANA's root zone database.

    The scraped data is written to standard output.
    """
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    print('[overrides]')

    logging.info("Scraping %s", ROOT_ZONE_DB)
    zone_page = requests.get(ROOT_ZONE_DB).text
    soup = BeautifulSoup(zone_page, 'html.parser')

    no_server = []
    for link in soup.select('#tld-table .tld a'):
        if 'href' not in link.attrs:
            continue

        # Is this a zone we should skip/ignore?
        row = link.parent.parent.parent.findChildren('td')
        if row[1].string == 'test':
            continue
        if row[2].string in ('Not assigned', 'Retired'):
            continue

        time.sleep(SLEEP)

        zone_url = urljoin(ROOT_ZONE_DB, link.attrs['href'])
        logging.info("Scraping %s", zone_url)
        b = requests.get(zone_url).text
        body = BeautifulSoup(b, 'html.parser')

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
            no_server.append(ace_zone)
        else:
            logging.info("WHOIS server for %s is %s", ace_zone, whois_server)
            print('%s=%s' % (ace_zone, whois_server))

    for ace_zone in no_server:
        print('; No record for %s' % ace_zone)

    logging.info("Done")

    return 0


if __name__ == '__main__':
    sys.exit(main())
