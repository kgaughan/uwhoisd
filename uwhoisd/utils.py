"""
Utilities.
"""

import collections
import contextlib
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import ConfigParser
import re
import StringIO
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
        with contextlib.closing(StringIO.StringIO(defaults)) as fp:
            parser.readfp(fp)
    if config_path is not None:
        parser.read(config_path)
    return parser


def is_well_formed_fqdn(fqdn):
    """
    Check if a string looks like a well formed FQDN.
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


# pylint: disable-msg=R0924
class Cache(object):
    """
    A simple LFU cache.
    """

    # This is implemented as an LFU cache. The eviction queue contains
    # 2-tuples consisting of the time the item was put into the cache and the
    # cache key. The cache maps cache keys onto 2-tuples consisting of a
    # counter giving the number of times this item occurs on the eviction queue
    # and the value.
    #
    # I may end up reimplementing this as an LRU cache if it turns out that's
    # more apt, but I haven't went that route as an LRU cache is somewhat more
    # awkward and involved to implement correctly.

    __slots__ = (
        'cache',
        'clock',
        'max_age',
        'max_size',
        'queue',
    )

    def __init__(self, max_size=256, max_age=300, clock=time.time):
        self.cache = {}
        self.queue = collections.deque()
        self.max_size = max_size
        self.max_age = max_age
        self.clock = clock

    def evict_one(self):
        """
        Remove the item at the head of the eviction cache.
        """
        _, key = self.queue.popleft()
        self.attempt_eviction(key)

    def attempt_eviction(self, key):
        """
        Attempt to remove the named item from the cache.
        """
        counter, value = self.cache[key]
        counter -= 1
        if counter == 0:
            del self.cache[key]
        else:
            self.cache[key] = (counter, value)

    def evict_expired(self):
        """
        Evict any items older than the maximum age from the cache.
        """
        cutoff = self.clock() - self.max_age
        while len(self.queue) > 0:
            ts, key = self.queue.popleft()
            if ts > cutoff:
                self.queue.appendleft((ts, key))
                break
            self.attempt_eviction(key)

    def __len__(self):
        return len(self.cache)

    def __contains__(self, key):
        return key in self.cache

    def __getitem__(self, key):
        if key not in self.cache:
            raise IndexError
        _, value = self.cache[key]
        # Force this onto the top of the heap.
        self[key] = value
        return value

    def __setitem__(self, key, value):
        if len(self.queue) == self.max_size:
            self.evict_one()
        if key in self.cache:
            counter, _ = self.cache[key]
        else:
            counter = 0
        self.cache[key] = (counter + 1, value)
        self.queue.append((self.clock(), key))
