from os import path

import bs4
import pytest

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


@pytest.mark.parametrize(
    "fragment",
    [
        "<html><body></body></html>",
        "<html><body><b>WHOIS Server:</b> </body></html>",
        "<html><body><b>WHOIS Server:</b></body></html>",
    ],
)
def test_extract_whois_server_no_matches(fragment):
    body = bs4.BeautifulSoup(fragment, "html.parser")
    result = scraper.extract_whois_server(body)
    assert result is None
