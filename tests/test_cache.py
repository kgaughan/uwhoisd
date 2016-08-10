from uwhoisd import caching
from . import utils


class LFU(caching.LFU):

    def __init__(self, max_size=256, max_age=300):
        self.clock = utils.Clock()
        super(LFU, self).__init__(max_size, max_age)


def test_insertion():
    cache = LFU()

    assert len(cache.cache) == 0
    assert len(cache.queue) == 0

    cache.set('a', 'x')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1
    assert cache.cache['a'] == (1, 'x')

    cache.set('b', 'y')
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2

    cache.set('a', 'z')
    assert len(cache.cache) == 2
    assert len(cache.queue) == 3
    assert cache.cache['a'] == (2, 'z')


def test_lfu():
    cache = LFU()

    cache.set('a', 'x')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1

    _ = cache.get('a')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'x')

    _ = cache.get('a')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 3
    assert cache.cache['a'] == (3, 'x')

    cache.evict_one()
    assert len(cache.cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'x')

    cache.evict_one()
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1
    assert cache.cache['a'] == (1, 'x')

    cache.evict_one()
    assert len(cache.cache) == 0
    assert len(cache.queue) == 0

    cache.set('a', 'x')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1

    cache.set('a', 'y')
    assert len(cache.cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'y')


def test_expiration():
    cache = LFU(max_age=5)

    # Ensure that the clock value is coming from the current value of the
    # `time` variable.
    assert cache.clock() == 0
    cache.clock.ticks = 2
    assert cache.clock() == 2

    cache.set('a', 'b')
    cache.set('b', 'c')

    cache.clock.ticks += 3

    cache.set('c', 'd')
    cache.set('d', 'e')

    assert len(cache.cache) == 4
    assert len(cache.queue) == 4
    cache.evict_expired()
    assert len(cache.cache) == 4
    assert len(cache.queue) == 4

    cache.clock.ticks += 3
    cache.evict_expired()
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2
    assert 'a' not in cache.cache
    assert 'b' not in cache.cache
    assert 'c' in cache.cache
    assert 'd' in cache.cache

    cache.set('c', 'f')
    assert len(cache.cache) == 2
    assert len(cache.queue) == 3

    cache.clock.ticks += 3
    cache.evict_expired()
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1
    assert 'c' in cache.cache
    assert cache.get('d') is None


def test_eviction():
    cache = LFU(max_size=2)
    cache.clock.ticks = 1

    cache.set('a', 1)
    cache.set('b', 2)
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2

    cache.set('c', 3)
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2
    assert sorted(cache.cache.keys()) == ['b', 'c']
