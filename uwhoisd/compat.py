"""
Python 2/3 compatibility layer.
"""

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


__all__ = (
    'SafeConfigParser',
    'urljoin',
)
