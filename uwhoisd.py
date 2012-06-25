#
# uwhoisd
# by Keith Gaughan <http://stereochro.me/>
#
# Copyright (c) Keith Gaughan, 2012
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

"""
A 'universal' WHOIS proxy server.
"""

import diesel
import re
import os.path
import sys
from ConfigParser import SafeConfigParser


__version__ = '0.0.1'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


USAGE = "Usage: %s <config>"


def read_config(parser):
    """
    Extract the configuration from a parsed configuration file, checking that
    the data contained within is valid.
    """
    # Ensure all sections are present, even if empty.
    for section in ('uwhoisd', 'overrides', 'prefixes', 'recursion_patterns'):
        if not parser.has_section(section):
            parser.add_section(section)

    def safe_get(section, option, default):
        """Get a configuration option safely."""
        if parser.has_option(section, option):
            return parser.get(section, option)
        return default

    iface = safe_get('uwhoisd', 'iface', '0.0.0.0')
    port = int(safe_get('uwhoisd', 'port', 4243))
    suffix = safe_get('uwhoisd', 'suffix', 'whois-servers.net')

    # TODO: Check all hostnames and zone names are well-formed.
    overrides = dict(parser.items('overrides'))
    prefixes = dict(parser.items('prefixes'))

    # We could use a compilation cache for these things, but the re module does
    # that anyway, so why bother.
    recursion_patterns = {}
    for zone, pattern in parser.items('recursion_patterns'):
        recursion_patterns[zone] = re.compile(pattern)

    return (iface, port, suffix, overrides, prefixes, recursion_patterns)


def respond(addr):
    query = diesel.until_eol()
    diesel.send("You sent: [%s]\n" % query.strip())


def main():
    """
    Execute the daemon.
    """
    if len(sys.argv) != 2:
        print >> sys.stderr, USAGE % os.path.basename(sys.argv[0])
        return 1

    parser = SafeConfigParser(allow_no_value=True)
    parser.read(sys.argv[1])
    iface, port, suffix, overrides, prefixes, recursion_patterns = \
        read_config(parser)

    diesel.quickstart(diesel.Service(respond, port, iface))


if __name__ == '__main__':
    main()
