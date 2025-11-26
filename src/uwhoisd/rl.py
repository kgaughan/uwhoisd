"""Rate limiting."""

import functools
import time


@functools.total_ordering
class TokenBucket:
    """A token bucket.

    Args:
        rate: token refill rate (per second) of bucket
        limit: maximum number of tokens the bucket can contain
    """

    __slots__ = [
        "_available",
        "limit",
        "rate",
        "ts",
    ]

    clock = staticmethod(time.time)

    def __init__(self, rate: int, limit: int) -> None:
        super().__init__()
        self.ts = self.clock()
        self.rate = rate
        self.limit = limit
        self._available = limit

    def consume(self, tokens: int) -> bool:
        """Attempt to remove the given number of tokens from this bucket.

        Args:
            tokens: number of tokens to consume

        Returns:
            `True` if the requested number could be consumed, otherwise `False`.
        """
        if 0 <= tokens <= self.tokens:
            self._available -= tokens
            return True
        return False

    @property
    def tokens(self):
        """Gives the number of tokens available in this bucket.

        Returns:
            The number of available tokens.
        """
        ts = self.clock()
        if self._available < self.limit:
            self._available += min((ts - self.ts) * self.rate, self.limit - self._available)
        self.ts = ts
        return self._available

    def __eq__(self, other):
        return self.ts == other.ts

    def __lt__(self, other):
        return self.ts < other.ts

    def __hash__(self):
        return hash((self._available, self.limit, self.rate, self.ts))

    def __getstate__(self):
        return dict(zip(self.__slots__, [getattr(self, attr) for attr in self.__slots__]))

    def __setstate__(self, state):
        for k in self.__slots__:
            setattr(self, k, state[k])
