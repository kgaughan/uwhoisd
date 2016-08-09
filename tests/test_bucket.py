import pickle

from uwhoisd.utils import TokenBucket


def test_creation():
    ticks = 42
    fake_clock = lambda: ticks

    bucket = TokenBucket(rate=23, limit=9000, clock=fake_clock)
    assert bucket.clock is fake_clock
    assert bucket.ts == ticks
    assert bucket.rate == 23
    assert bucket.limit == 9000
    assert bucket._available == bucket.limit


def test_consumption():
    ticks = 0
    fake_clock = lambda: ticks

    bucket = TokenBucket(5, 20, clock=fake_clock)
    assert bucket.tokens == 20
    assert bucket.consume(10)
    assert not bucket.consume(15)
    assert bucket.tokens == 10

    ticks += 1
    assert bucket.tokens == 15
    ticks += 2
    assert bucket.tokens == 20

    assert bucket.consume(1)
    assert bucket.tokens == 19
    ticks += 1
    assert bucket.tokens == 20


def test_comparison():
    ticks = 0
    fake_clock = lambda: ticks

    b1 = TokenBucket(5, 20, clock=fake_clock)
    b2 = TokenBucket(5, 20, clock=fake_clock)

    # These comparisons check when the buckets were last *used*, not the number
    # of tokens each contains.
    assert b1 == b2
    ticks += 1
    b1.consume(1)
    assert b2 < b1
    ticks += 1
    b2.consume(1)
    assert b1 < b2
    ticks += 1
    b1.consume(1)
    b2.consume(1)
    assert b1 == b2


def test_pickle():
    original = TokenBucket(5, 20)
    original.consume(1)
    unpickled = pickle.loads(pickle.dumps(original))
    assert unpickled is not original
    assert original.clock is unpickled.clock
    assert original.ts == unpickled.ts
    assert original.rate == unpickled.rate
    assert original.limit == unpickled.limit
    assert original._available == unpickled._available
