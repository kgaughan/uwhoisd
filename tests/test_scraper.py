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
