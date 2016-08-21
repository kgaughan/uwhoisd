"""
Python 2/3 compatibility layer.
"""

try:
    import configparser as _cp
except ImportError:
    import ConfigParser as _cp
import sys
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


__all__ = (
    'ESCAPE_CODEC',
    'SafeConfigParser',
    'urljoin',
)


PY2 = sys.version_info < (3,)

ESCAPE_CODEC = 'string_escape' if PY2 else 'unicode_escape'


if PY2:
    import io

    class SafeConfigParser(_cp.SafeConfigParser):  # noqa: D101

        def read_string(self, string):  # noqa: D102
            self.readfp(io.StringIO(string))
else:
    SafeConfigParser = _cp.SafeConfigParser
