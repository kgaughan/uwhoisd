import pytest

from uwhoisd import utils


def test_is_well_formed_fqdn():
    assert utils.is_well_formed_fqdn("stereochro.me")
    assert utils.is_well_formed_fqdn("bbc.co.uk")
    assert utils.is_well_formed_fqdn("x" * 63 + ".com")


def test_malformed_domains():
    assert not utils.is_well_formed_fqdn("stereochrome"), "Must have more than one label"
    assert not utils.is_well_formed_fqdn("stereochr.me."), "No trailing dot allowed"
    assert not utils.is_well_formed_fqdn(".stereochr.me"), "No leading dot allowed"
    assert not utils.is_well_formed_fqdn("stereochrome."), "Sigh..."
    assert not utils.is_well_formed_fqdn("invalid domain.com"), "No spaces allowed"
    assert not utils.is_well_formed_fqdn(""), "Must not be an empty string"
    assert not utils.is_well_formed_fqdn("."), "Must have at least one label"
    assert not utils.is_well_formed_fqdn("x" * 64 + ".foo"), "Labels should not exceed 63 characters (1)"
    assert not utils.is_well_formed_fqdn("foo." + "x" * 64), "Labels should not exceed 63 characters (2)"


def test_split_fqdn():
    assert utils.split_fqdn("stereochro.me") == ["stereochro", "me"]
    assert utils.split_fqdn("stereochro.me.") == ["stereochro", "me"]
    assert utils.split_fqdn("stereochrome") == ["stereochrome"]
    assert utils.split_fqdn("bbc.co.uk") == ["bbc", "co.uk"]
    assert utils.split_fqdn("") == []


def test_decode_value():
    assert utils.decode_value("foo") == "foo"
    assert utils.decode_value('"foo"') == "foo"
    assert utils.decode_value('"foo\nbar"') == "foo\nbar"
    assert utils.decode_value("foo\nbar") == "foo\nbar"
    assert utils.decode_value('""') == ""
    assert utils.decode_value("''") == ""

    for bad_value in ['"foo', "'foo", "\"foo'"]:
        with pytest.raises(ValueError, match=r"The trailing quote be present and match the leading quote\."):
            utils.decode_value(bad_value)
