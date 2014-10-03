"""
A scraper which pulls zone WHOIS servers from IANA's root zone database.
"""

import csv
import logging
import socket
import StringIO
import sys
import time
import urlparse

import beautifulscraper


ROOT_ZONE_DB = 'http://www.iana.org/domains/root/db'
SLEEP = 0

IP_ASSIGNATIONS = 'https://www.iana.org/assignments/ipv4-address-space/ipv4-address-space.csv'


def ip_assignations(scraper):
    logging.info("Scraping %s", IP_ASSIGNATIONS)
    assignations = scraper.go(IP_ASSIGNATIONS)
    print assignations
    reader = csv.reader(StringIO.StringIO(assignations))
    next(reader, None)
    no_server = []
    for p, designation, date, whois_server, status, note in reader:
        prefix = int(p[0:3])
        if whois_server == '':
            logging.info("No WHOIS server found for %s", prefix)
            no_server.append(prefix)
        else:
            logging.info("WHOIS server for %s is %s", prefix, whois_server)
            print '%s=%s' % (prefix, whois_server)
    for prefix in no_server:
        print '; No record for %s' % prefix


def main():
    """
    Scrape IANA's root zone database and write the resulting configuration
    data to stdout.
    """
    print '[overrides]'

    logging.info("Scraping %s", ROOT_ZONE_DB)
    scraper = beautifulscraper.BeautifulScraper()
    body = scraper.go(ROOT_ZONE_DB)

    no_server = []
    for link in body.select('#tld-table .tld a'):
        if 'href' not in link.attrs:
            continue

        time.sleep(SLEEP)

        zone_url = urlparse.urljoin(ROOT_ZONE_DB, link.attrs['href'])
        body = scraper.go(zone_url)

        title = body.find('h1')
        if title is None:
            continue
        title_parts = title.string.split('.', 1)
        if len(title_parts) != 2:
            continue
        ace_zone = title_parts[1].encode('idna').lower()

        whois_server_label = body.find('b', text='WHOIS Server:')
        whois_server = ''
        if whois_server_label is not None:
            whois_server = whois_server_label.next_sibling.strip().lower()

        # Fallback to trying whois.nic.*
        if whois_server == '':
            whois_server = 'whois.nic.%s' % ace_zone
            logging.info("Trying %s", whois_server)
            try:
                socket.gethostbyname(whois_server)
            except socket.gaierror:
                whois_server = ''

        if whois_server == '':
            logging.info("No WHOIS server found for %s", ace_zone)
            no_server.append(ace_zone)
        else:
            logging.info("WHOIS server for %s is %s", ace_zone, whois_server)
            print '%s=%s' % (ace_zone, whois_server)

    for ace_zone in no_server:
        print '; No record for %s' % ace_zone

    ip_assignations(scraper)

    return 0


if __name__ == '__main__':
    sys.exit(main())
