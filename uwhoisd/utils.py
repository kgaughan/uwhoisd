"""
Utilities.
"""

import contextlib
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import glob
import os.path
import re

import pkg_resources


# We only accept ASCII or ACE-encoded domain names. IDNs must be converted
# to ACE first.
FQDN_PATTERN = re.compile(r'^([-a-z0-9]{1,63})(\.[-a-z0-9]{1,63}){1,}$')


class ConfigParser(configparser.SafeConfigParser):
    """
    Enhanced configuration parser.
    """

    def get_bool(self, section, option):
        """
        Get a configuration option as a boolean.
        """
        return self.get(section, option).lower() in ('1', 'true', 'yes', 'on')

    def get_list(self, section, option):
        """
        Split the lines of a configuration option value into a list.
        """
        lines = []
        for line in self.get(section, option).split("\n"):
            line = line.strip()
            if line != '':
                lines.append(line)
        return lines

    def get_section_dict(self, section):
        """
        Pull a section out of the config as a dictionary safely.
        """
        if self.has_section(section):
            return dict((key, decode_value(value))
                        for key, value in self.items(section))
        return {}


def make_config_parser(config_path=None):
    """
    Create a config parser.
    """
    parser = ConfigParser()

    with contextlib.closing(
            pkg_resources.resource_stream('uwhoisd', 'defaults.ini')) as fp:
        parser.readfp(fp)

    if config_path is not None:
        parser.read(config_path)
        if parser.has_option('include', 'path'):
            glob_path = os.path.join(os.path.dirname(config_path),
                                     parser.get('include', 'path'))
            parser.read(glob.glob(glob_path))

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
    >>> is_well_formed_fqdn('')
    False
    >>> is_well_formed_fqdn('.')
    False
    >>> is_well_formed_fqdn('x' * 64 + '.foo')
    False
    >>> is_well_formed_fqdn('foo.' + 'x' * 64)
    False
    """
    return FQDN_PATTERN.match(fqdn) is not None


def split_fqdn(fqdn):
    """
    Split an FQDN into the domain name and zone.

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


def decode_value(s):
    r"""
    Decode a quoted string.

    If a string is quoted, it's parsed like a python string, otherwise it's
    passed straight through as-is.

    >>> decode_value('foo')
    'foo'
    >>> decode_value('"foo"')
    'foo'
    >>> decode_value('"foo\\nbar"')
    'foo\nbar'
    >>> decode_value('foo\nbar')
    'foo\nbar'
    >>> decode_value('"foo')
    Traceback (most recent call last):
        ...
    ValueError: The trailing quote be present and match the leading quote.
    >>> decode_value("'foo")
    Traceback (most recent call last):
        ...
    ValueError: The trailing quote be present and match the leading quote.
    >>> decode_value("\"foo\'")
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
