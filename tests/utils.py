"""
Utility functions for testing.
"""

from os import path

import uwhoisd


HERE = path.dirname(__file__)


def create_uwhois():
    """Prepare a UWhois object for testing."""
    parser = uwhoisd.make_default_config_parser()
    parser.read(path.join(HERE, '..', 'uwhoisd.ini'))
    uwhois = uwhoisd.UWhois()
    uwhois.read_config(parser)
    return uwhois


def read_transcript(name):
    """Read a WHOIS transcript file."""
    with open(path.join(HERE, 'transcripts', name), 'r') as fh:
        return fh.read()
