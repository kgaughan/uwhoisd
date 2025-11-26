import pytest

from uwhoisd import utils


@pytest.mark.parametrize("fqdn", ["stereochro.me", "bbc.co.uk", "x" * 63 + ".com"])
def test_is_well_formed_fqdn(fqdn):
    assert utils.is_well_formed_fqdn(fqdn)


@pytest.mark.parametrize(
    "fqdn",
    [
        "stereochrome",
        "stereochr.me.",
        ".stereochr.me",
        "stereochrome.",
        "invalid domain.com",
        ".",
        "",
        "x" * 64 + ".foo",
        "foo." + "x" * 64,
    ],
)
def test_malformed_domains(fqdn):
    assert not utils.is_well_formed_fqdn(fqdn)


@pytest.mark.parametrize(
    "pair",
    [
        ("stereochro.me", ["stereochro", "me"]),
        ("stereochro.me.", ["stereochro", "me"]),
        ("stereochrome", ["stereochrome"]),
        ("bbc.co.uk", ["bbc", "co.uk"]),
        ("", []),
    ],
)
def test_split_fqdn(pair):
    to_split, expected = pair
    assert utils.split_fqdn(to_split) == expected


@pytest.mark.parametrize(
    "pair",
    [
        ("foo", "foo"),
        ('"foo"', "foo"),
        ('"foo\nbar"', "foo\nbar"),
        ("foo\nbar", "foo\nbar"),
        ('""', ""),
        ("''", ""),
    ],
)
def test_decode_value(pair):
    to_decode, expected = pair
    assert utils.decode_value(to_decode) == expected


@pytest.mark.parametrize("bad", ['"foo', "'foo", "\"foo'"])
def test_undecodable(bad):
    with pytest.raises(ValueError, match=r"The trailing quote be present and match the leading quote\."):
        utils.decode_value(bad)
