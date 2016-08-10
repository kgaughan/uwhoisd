import collections
import logging
import time

import pkg_resources


logger = logging.getLogger('uwhoisd')


class UnknownCache(Exception):
    """
    The supplied cache type name cannot be found.
    """


def get_cache(cfg):
    """
    Attempt to load the configured cache.
    """
    cache_name = cfg.pop('type', 'null')
    if cache_name == 'null':
        logger.info("Caching deactivated")
        return None
    for ep in pkg_resources.iter_entry_points('uwhoisd.cache'):
        if ep.name == cache_name:
            logger.info("Using cache '%s' with the parameters %r",
                        cache_name, cfg)
            cache_type = ep.load()
            return cache_type(**cfg)
    raise UnknownCache(cache_name)


def wrap_whois(cache, whois_func):
    """
    Wrap a WHOIS query function with a cache.
    """
    if cache is None:
        return whois_func

    def wrapped(query):
        """
        Caching wrapper around whois callable.
        """
        cache.evict_expired()
        if query in cache:
            logger.info("Cache hit for %s", query)
            response = cache[query]
        else:
            response = whois_func(query)
            cache[query] = response
        return response
    return wrapped


# pylint: disable-msg=R0924
class LFU(object):
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
        'max_age',
        'max_size',
        'queue',
    )

    clock = staticmethod(time.time)

    def __init__(self, max_size=256, max_age=300):
        super(LFU, self).__init__()
        self.cache = {}
        self.queue = collections.deque()
        self.max_size = int(max_size)
        self.max_age = int(max_age)

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
