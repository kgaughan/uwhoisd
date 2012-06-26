from uwhoisd import Cache


def test_insertion():
    cache = Cache()

    assert len(cache.cache) == 0
    assert len(cache.queue) == 0

    cache['a'] = 'x'
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1
    assert cache.cache['a'] == (1, 'x')

    cache['b'] = 'y'
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2

    cache['a'] = 'z'
    assert len(cache.cache) == 2
    assert len(cache.queue) == 3
    assert cache.cache['a'] == (2, 'z')


def test_lfu():
    cache = Cache()

    cache['a'] = 'x'
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1

    _ = cache['a']
    assert len(cache.cache) == 1
    assert len(cache.queue) == 2
    assert cache.cache['a'] == (2, 'x')

    _ = cache['a']
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


def test_expiration():
    time = 1

    cache = Cache(max_age=5, clock=lambda:time)

    # Ensure that the clock value is coming from the current value of the
    # `time` variable.
    assert cache.clock() == 1
    time = 2
    assert cache.clock() == 2

    cache['a'] = 'b'
    cache['b'] = 'c'

    time += 3

    cache['c'] = 'd'
    cache['d'] = 'e'

    assert len(cache.cache) == 4
    assert len(cache.queue) == 4
    cache.evict_expired()
    assert len(cache.cache) == 4
    assert len(cache.queue) == 4

    time += 3
    cache.evict_expired()
    assert len(cache.cache) == 2
    assert len(cache.queue) == 2
    assert 'c' in cache.cache
    assert 'd' in cache.cache

    cache['c'] = 'f'
    assert len(cache.cache) == 2
    assert len(cache.queue) == 3

    time += 3
    cache.evict_expired()
    assert len(cache.cache) == 1
    assert len(cache.queue) == 1
    assert 'c' in cache.cache
