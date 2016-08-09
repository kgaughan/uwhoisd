"""
Utilities.
"""

import contextlib
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import io
import re
import time


# We only accept ASCII or ACE-encoded domain names. IDNs must be converted
# to ACE first.
FQDN_PATTERN = re.compile(r'^([-a-z0-9]{1,63})(\.[-a-z0-9]{1,63}){1,}$')


def make_config_parser(defaults=None, config_path=None):
    """
    Creates a config parser.
    """
    parser = configparser.SafeConfigParser()
    if defaults is not None:
        with contextlib.closing(io.StringIO(defaults)) as fp:
            parser.readfp(fp)
    if config_path is not None:
        parser.read(config_path)
    return parser


def is_well_formed_fqdn(fqdn):
    """
    Check if a string looks like a well formed FQDN without a trailing dot.

    >>> is_well_formed_fqdn('stereochro.me')
    True
    >>> is_well_formed_fqdn('stereochro.me.')
    False
    >>> is_well_formed_fqdn('stereochrome')
    False
    >>> is_well_formed_fqdn('stereochrome.')
    False
    >>> is_well_formed_fqdn('keithgaughan.co.uk')
    True
    """
    return FQDN_PATTERN.match(fqdn) is not None


def split_fqdn(fqdn):
    """
    Splits an FQDN into the domain name and zone.

    >>> split_fqdn('stereochro.me')
    ['stereochro', 'me']
    >>> split_fqdn('stereochro.me.')
    ['stereochro', 'me']
    >>> split_fqdn('stereochrome')
    ['stereochrome']
    >>> split_fqdn('keithgaughan.co.uk')
    ['keithgaughan', 'co.uk']
    """
    return fqdn.rstrip('.').split('.', 1)


def to_bool(s):
    """
    Converts the given string to a boolean.
    """
    return s.lower() in ('1', 'true', 'yes', 'on')


def decode_value(s):
    """
    If a string is quoted, it's parsed like a python string, otherwise it's
    passed straight through as-is.

    >>> decode_value('foo')
    'foo'
    >>> decode_value('"foo"')
    'foo'
    >>> decode_value('"foo\\\\nbar\"')
    'foo\\nbar'
    >>> decode_value('foo\\nbar')
    'foo\\nbar'
    >>> decode_value('"foo')
    Traceback (most recent call last):
        ...
    ValueError: The trailing quote be present and match the leading quote.
    >>> decode_value("'foo")
    Traceback (most recent call last):
        ...
    ValueError: The trailing quote be present and match the leading quote.
    >>> decode_value("\\\"foo\\'")
    Traceback (most recent call last):
        ...
    ValueError: The trailing quote be present and match the leading quote.
    """
    if len(s) > 1 and s[0] in ('"', "'"):
        if s[0] != s[-1]:
            raise ValueError(
                "The trailing quote be present and match the leading quote.")
        return s[1:-1].decode('string_escape')
    return s
