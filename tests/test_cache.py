from uwhoisd import caching
from . import utils


class LFU(caching.LFU):

    def __init__(self, max_size=256, max_age=300):
        self.clock = utils.Clock()
        super(LFU, self).__init__(max_size, max_age)


def test_insertion():
    cache = LFU()

    assert len(cache) == 0
    assert len(cache.queue) == 0

    cache['a'] = 'x'
    assert len(cache) == 1
    assert len(cache.queue) == 1
    assert cache.cache['a'] == (1, 'x')

    cache['b'] = 'y'
    assert len(cache) == 2
    assert len(cache.queue) == 2

    cache['a'] = 'z'
    assert len(cache) == 2
    assert len(cache.queue) == 3
    assert cache.cache['a'] == (2, 'z')


def test_lfu():
    cache = LFU()

    cache['a'] = 'x'
    assert len(cache) == 1
    assert len(cache.queue) == 1

    _ = cache['a']
    assert len(cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'x')

    _ = cache['a']
    assert len(cache) == 1
    assert len(cache.queue) == 3
    assert cache.cache['a'] == (3, 'x')

    cache.evict_one()
    assert len(cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'x')

    cache.evict_one()
    assert len(cache) == 1
    assert len(cache.queue) == 1
    assert cache.cache['a'] == (1, 'x')

    cache.evict_one()
    assert len(cache) == 0
    assert len(cache.queue) == 0

    cache['a'] = 'x'
    assert len(cache) == 1
    assert len(cache.queue) == 1

    cache['a'] = 'y'
    assert len(cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'y')


def test_expiration():
    cache = LFU(max_age=5)

    # Ensure that the clock value is coming from the current value of the
    # `time` variable.
    assert cache.clock() == 0
    cache.clock.ticks = 2
    assert cache.clock() == 2

    cache['a'] = 'b'
    cache['b'] = 'c'

    cache.clock.ticks += 3

    cache['c'] = 'd'
    cache['d'] = 'e'

    assert len(cache) == 4
    assert len(cache.queue) == 4
    cache.evict_expired()
    assert len(cache) == 4
    assert len(cache.queue) == 4

    cache.clock.ticks += 3
    cache.evict_expired()
    assert len(cache) == 2
    assert len(cache.queue) == 2
    assert 'a' not in cache
    assert 'b' not in cache
    assert 'c' in cache
    assert 'd' in cache

    cache['c'] = 'f'
    assert len(cache) == 2
    assert len(cache.queue) == 3

    cache.clock.ticks += 3
    cache.evict_expired()
    assert len(cache) == 1
    assert len(cache.queue) == 1
    assert 'c' in cache
    try:
        _ = cache['d']
        assert False, "'d' should not be in cache"
    except IndexError:
        pass


def test_eviction():
    cache = LFU(max_size=2)
    cache.clock.ticks = 1

    cache['a'] = 1
    cache['b'] = 2
    assert len(cache) == 2
    assert len(cache.queue) == 2

    cache['c'] = 3
    assert len(cache) == 2
    assert len(cache.queue) == 2
    assert sorted(cache.cache.keys()) == ['b', 'c']
