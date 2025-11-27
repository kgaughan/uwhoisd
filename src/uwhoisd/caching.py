"""Caching support."""

import collections
from importlib import metadata
import logging
import time
import typing as t

logger = logging.getLogger(__name__)


class Cache(t.Protocol):
    """A WHOIS cache protocol."""

    def get(self, key: str) -> t.Optional[str]:
        """Retrieve a value from the cache.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value, or `None` if not found.
        """

    def set(self, key: str, value: str) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key to store the value under.
            value: The value to store.
        """


class UnknownCacheError(Exception):
    """The supplied cache type name cannot be found."""


def get_cache(cfg: dict[str, str]) -> t.Optional[Cache]:
    """Attempt to load the configured cache.

    Args:
        cfg: The cache configuration. Must contain a "type" key giving the
            cache type name. Any other keys are passed as parameters to the
            cache constructor.

    Returns: The cache object, or `None` if caching is disabled.
    """
    cache_name = cfg.pop("type", "null")
    if cache_name == "null":
        logger.info("Caching deactivated")
        return None
    eps = metadata.entry_points()
    for ep in eps.get("uwhoisd.cache", []):
        if ep.name == cache_name:
            logger.info("Using cache '%s' with the parameters %r", cache_name, cfg)
            cache_type = ep.load()
            return cache_type(**cfg)
    raise UnknownCacheError(cache_name)


def wrap_whois(
    cache: t.Optional[Cache],
    whois_func: t.Callable[[str], t.Awaitable[str]],
) -> t.Callable[[str], t.Awaitable[str]]:
    """Wrap a WHOIS query function with a cache.

    Args:
        cache: The cache to use, or `None` to disable caching.
        whois_func: The WHOIS query function to wrap.

    Returns:
        The wrapped WHOIS query function.
    """
    if cache is None:
        return whois_func

    async def wrapped(query: str) -> str:
        response = cache.get(query)
        if response is None:
            response = await whois_func(query)
            cache.set(query, response)
        else:
            logger.info("Cache hit for '%s'", query)
        return response

    return wrapped


class LFU:
    """A simple LFU cache.

    The eviction queue contains 2-tuples consisting of the time the item was
    put into the cache and the cache key. The cache maps cache keys onto
    2-tuples consisting of a counter giving the number of times this item
    occurs on the eviction queue and the value.

    Args:
        max_size: Maximum number of entries the cache can contain.
        max_age: Maximum number of seconds to consider an entry live.
    """

    # I may end up reimplementing an LRU cache if it turns out that's more apt,
    # but I haven't went that route as an LRU cache is somewhat more awkward
    # and involved to implement correctly.

    __slots__ = (
        "cache",
        "max_age",
        "max_size",
        "queue",
    )

    clock = staticmethod(time.time)

    def __init__(self, max_size: int = 256, max_age: int = 300) -> None:
        super().__init__()
        self.cache: dict[str, tuple[int, str]] = {}
        self.queue: t.Deque[tuple[int, str]] = collections.deque()
        self.max_size = int(max_size)
        self.max_age = int(max_age)

    def evict_one(self) -> None:
        """Remove the item at the head of the eviction cache."""
        _, key = self.queue.popleft()
        self.attempt_eviction(key)

    def attempt_eviction(self, key: str) -> None:
        """Attempt to remove the named item from the cache.

        Args:
            key: The cache key to evict.
        """
        counter, value = self.cache[key]
        counter -= 1
        if counter == 0:
            del self.cache[key]
        else:
            self.cache[key] = (counter, value)

    def evict_expired(self) -> None:
        """Evict any items older than the maximum age from the cache."""
        cutoff = self.clock() - self.max_age
        while len(self.queue) > 0:
            ts, key = self.queue.popleft()
            if ts > cutoff:
                self.queue.appendleft((ts, key))
                break
            self.attempt_eviction(key)

    def get(self, key: str) -> t.Optional[str]:
        """Pull a value from the cache corresponding to the key.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value, or `None` if not found.
        """
        self.evict_expired()
        if key not in self.cache:
            return None
        _, value = self.cache[key]
        # Force this onto the top of the queue.
        self.set(key, value)
        return value

    def set(self, key: str, value: str) -> None:
        """Add `value` to the cache, to be referenced by `key`.

        Args:
            key: The cache key to store the value under.
            value: The value to store.
        """
        if len(self.queue) == self.max_size:
            self.evict_one()
        if key in self.cache:
            counter, _ = self.cache[key]
        else:
            counter = 0
        self.cache[key] = (counter + 1, value)
        self.queue.append((int(self.clock()), key))
