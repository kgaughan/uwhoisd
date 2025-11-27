"""Utilities."""

import codecs
import configparser
import glob
from importlib import resources
import os.path
import re
import typing as t

# We only accept ASCII or ACE-encoded domain names. IDNs must be converted
# to ACE first.
FQDN_PATTERN = re.compile(r"^([-a-z0-9]{1,63})(\.[-a-z0-9]{1,63}){1,}$")


class ConfigParser(configparser.ConfigParser):
    """Enhanced configuration parser."""

    def get_bool(self, section: str, option: str) -> bool:
        """Get a configuration option as a boolean.

        Args:
            section: The config section.
            option: The config option.

        Returns:
            The boolean value of the option.
        """
        return self.get(section, option).lower() in ("1", "true", "yes", "on")

    def get_list(self, section: str, option: str) -> t.List[str]:
        """Split the lines of a configuration option value into a list.

        Args:
            section: The config section.
            option: The config option.

        Returns:
            The list of lines.
        """
        lines = []
        for line in self.get(section, option).split("\n"):
            line = line.strip()
            if line != "":
                lines.append(line)
        return lines

    def get_section_dict(self, section: str) -> t.Dict[str, str]:
        """Pull a section out of the config as a dictionary safely."""
        if self.has_section(section):
            return {key: decode_value(value) for key, value in self.items(section)}
        return {}


def make_config_parser(config_path: t.Optional[str] = None) -> ConfigParser:
    """Create a config parser.

    This will load the default config from the package, and then overlay
    any config file specified by `config_path`. If the config file contains
    an `[include]` section with a `path` option, any files matching that
    glob will also be loaded.

    Args:
        config_path: Optional path to a config file to load.

    Returns:
        The config parser.
    """
    parser = ConfigParser()

    with resources.open_text("uwhoisd", "defaults.ini", encoding="utf-8") as fh:
        parser.read_file(fh)

    if config_path is not None:
        parser.read(config_path)
        if parser.has_option("include", "path"):
            glob_path = os.path.join(os.path.dirname(config_path), parser.get("include", "path"))
            parser.read(glob.glob(glob_path))

    return parser


def is_well_formed_fqdn(fqdn: str) -> bool:
    """Check if a string looks like a well formed FQDN without a trailing dot.

    Args:
        fqdn: The FQDN to check.

    Returns:
        True if the FQDN is well formed, False otherwise.
    """
    return FQDN_PATTERN.match(fqdn) is not None


def split_fqdn(fqdn: str) -> t.List[str]:
    """Split an FQDN into the domain name and zone.

    Args:
        fqdn: The FQDN to split.

    Returns:
        A list of [domain name, zone], or an empty list if the FQDN is empty.
    """
    return fqdn.rstrip(".").split(".", 1) if fqdn else []


def decode_value(s: str) -> str:
    """Decode a quoted string.

    If a string is quoted, it's parsed like a python string, otherwise it's
    passed straight through as-is.

    Args:
        s: The string to decode.

    Returns:
        The decoded string.
    """
    if len(s) > 1 and s[0] in ('"', "'"):
        if s[0] != s[-1]:
            raise ValueError("The trailing quote be present and match the leading quote.")
        return codecs.decode(s[1:-1], "unicode_escape")
    return s
