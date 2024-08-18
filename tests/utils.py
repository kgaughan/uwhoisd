"""
Utility functions for testing.
"""

from os import path

import uwhoisd
from uwhoisd.utils import make_config_parser

HERE = path.dirname(__file__)


class Clock:
    """
    A fake clock.
    """

    def __init__(self, initial: int = 0):
        super().__init__()
        self.ticks = initial

    def __call__(self):
        return self.ticks


def create_uwhois() -> uwhoisd.UWhois:
    """Prepare a UWhois object for testing."""
    config = path.join(HERE, "..", "extra", "uwhoisd.ini")
    parser = make_config_parser(config)
    uwhois = uwhoisd.UWhois()
    uwhois.read_config(parser)
    return uwhois


def read_transcript(name: str) -> str:
    """Read a WHOIS transcript file."""
    with open(path.join(HERE, "transcripts", name)) as fh:
        return fh.read()
