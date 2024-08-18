import pickle

from uwhoisd import rl

from . import utils


class TokenBucket(rl.TokenBucket):
    """
    A token bucket with a fake clock.
    """

    def __init__(self, rate, limit, clock=None):
        self.clock = utils.Clock() if clock is None else clock
        super().__init__(rate, limit)


def test_creation():
    fake_clock = utils.Clock(42)
    bucket = TokenBucket(rate=23, limit=9000, clock=fake_clock)
    assert bucket.clock is fake_clock
    assert bucket.ts == 42
    assert bucket.rate == 23
    assert bucket.limit == 9000
    assert bucket._available == bucket.limit


def test_consumption():
    bucket = TokenBucket(5, 20)
    assert bucket.tokens == 20
    assert bucket.consume(10)
    assert not bucket.consume(15)
    assert bucket.tokens == 10

    bucket.clock.ticks += 1
    assert bucket.tokens == 15
    bucket.clock.ticks += 2
    assert bucket.tokens == 20

    assert bucket.consume(1)
    assert bucket.tokens == 19
    bucket.clock.ticks += 1
    assert bucket.tokens == 20


def test_comparison():
    clock = utils.Clock()
    b1 = TokenBucket(5, 20, clock=clock)
    b2 = TokenBucket(5, 20, clock=clock)

    # These comparisons check when the buckets were last *used*, not the number
    # of tokens each contains.
    assert b1 == b2
    clock.ticks += 1
    b1.consume(1)
    assert b2 < b1
    clock.ticks += 1
    b2.consume(1)
    assert b1 < b2
    clock.ticks += 1
    b1.consume(1)
    b2.consume(1)
    assert b1 == b2


def test_pickle():
    original = rl.TokenBucket(5, 20)
    original.consume(1)
    unpickled = pickle.loads(pickle.dumps(original))
    assert unpickled is not original
    assert original.clock is unpickled.clock
    assert original.ts == unpickled.ts
    assert original.rate == unpickled.rate
    assert original.limit == unpickled.limit
    assert original._available == unpickled._available
