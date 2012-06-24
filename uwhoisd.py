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


__version__ = '0.0.1'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


USAGE = "Usage: %s <config>"

DEFAULTS = {
    'uwhoisd': {
        'interface': '0.0.0.0',
        'port': 4243,
        'default_suffix': 'whois-servers.net'
    }
}


def read_config(parser):
    """
    Extract the configuration from a parsed configuration file, checking that
    the data contained within is valid.
    """
    # interface, port, default_suffix, overrides, prefixes, recursion_patterns
    return ('', 0, '', [], [], [])


def respond(addr):
    query = diesel.until_eol()
    diesel.send("You sent: [%s]\n" % query.strip())


def main():
    diesel.quickstart(diesel.Service(respond, 1043))


if __name__ == '__main__':
    main()
