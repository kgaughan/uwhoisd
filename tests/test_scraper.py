from os import path

import bs4

from uwhoisd import scraper

HERE = path.dirname(__file__)


def test_extract_zone_urls():
    with open(path.join(path.dirname(__file__), "iana-root-zone.html"), encoding="utf-8") as fh:
        body = bs4.BeautifulSoup(fh, "html.parser")
    result = list(scraper.extract_zone_urls("http://example.com", body))
    # The test zone should not appear
    assert result == [
        ("aaa", "http://example.com/domains/root/db/aaa.html"),
        ("bt", "http://example.com/domains/root/db/bt.html"),
        ("xxx", "http://example.com/domains/root/db/xxx.html"),
    ]


def test_extract_zone_urls_edge_cases():
    empty_body = bs4.BeautifulSoup("", "html.parser")
    assert list(scraper.extract_zone_urls("http://example.com", empty_body)) == []


def test_extract_whois_server():
    with open(path.join(path.dirname(__file__), "zone-info-fragment.html"), encoding="utf-8") as fh:
        body = bs4.BeautifulSoup(fh, "html.parser")
    result = scraper.extract_whois_server(body)
    assert result == "whois.nic.abc"


def test_extract_whois_server_not_found():
    body = bs4.BeautifulSoup("<html><body></body></html>", "html.parser")
    result = scraper.extract_whois_server(body)
    assert result is None


def test_extract_whois_server_empty_sibling():
    body = bs4.BeautifulSoup("<html><body><b>WHOIS Server:</b> </body></html>", "html.parser")
    result = scraper.extract_whois_server(body)
    assert result is None


def test_extract_whois_server_no_sibling():
    body = bs4.BeautifulSoup("<html><body><b>WHOIS Server:</b></body></html>", "html.parser")
    result = scraper.extract_whois_server(body)
    assert result is None
