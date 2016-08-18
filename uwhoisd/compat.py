"""
Python 2/3 compatibility layer.
"""

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser


__all__ = (
    'SafeConfigParser',
)
