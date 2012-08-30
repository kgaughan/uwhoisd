from tests import utils


def test_recursion():
    uwhois = utils.create_uwhois()
    expected = 'whois.markmonitor.com'
    transcript = utils.read_transcript('google.com.txt')
    # Make sure there's nothing wrong with the WHOIS transcript.
    assert transcript.count(expected) == 1
    assert uwhois.get_registrar_whois_server('com', transcript) == expected
