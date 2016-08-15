"""
Rate limiting.
"""

import time


class TokenBucket(object):
    """
    A token bucket.
    """

    __slots__ = (
        'ts',
        'rate',
        'limit',
        '_available',
    )

    clock = staticmethod(time.time)

    def __init__(self, rate, limit):
        """
        Create a new token bucket.

        :param rate int: Token refill rate (per second) of bucket.
        :param limit int: Maximum number of tokens the bucket can contain.
        """
        super(TokenBucket, self).__init__()
        self.ts = self.clock()
        self.rate = rate
        self.limit = limit
        self._available = limit

    def consume(self, tokens):
        """
        Attempt to remove the given number of tokens from this bucket.

        If there are enough tokens in the bucket to fulfil the request, we
        return `True`, otherwise `False`.
        """
        if 0 <= tokens <= self.tokens:
            self._available -= tokens
            return True
        return False

    @property
    def tokens(self):
        """
        The number of tokens available in this bucket.
        """
        ts = self.clock()
        if self._available < self.limit:
            self._available += min(
                (ts - self.ts) * self.rate,
                self.limit - self._available)
        self.ts = ts
        return self._available

    def __cmp__(self, other):
        return cmp(self.ts, other.ts)

    def __getstate__(self):
        return dict(zip(
            self.__slots__,
            [getattr(self, attr) for attr in self.__slots__]))

    def __setstate__(self, state):
        for k in self.__slots__:
            setattr(self, k, state[k])
