import collections
import time


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