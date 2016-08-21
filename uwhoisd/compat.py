"""
Python 2/3 compatibility layer.
"""

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser
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
