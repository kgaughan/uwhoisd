#!/usr/bin/env python

from setuptools import setup
import re


def read(filename):
    with open(filename, 'r') as fh:
        return fh.read()


def get_metadata(module_path):
    """Extract the metadata from a module file."""
    matches = re.finditer(
        r"^__(\w+?)__ *= *'(.*?)'$",
        read(module_path),
        re.MULTILINE)
    return dict(
        (match.group(1), match.group(2).decode('unicode_escape'))
        for match in matches)


def read_requirements(requirements_path):
    """Read a requirements file, stripping out the detritus."""
    requirements = []
    with open(requirements_path, 'r') as fh:
        for line in fh:
            line = line.strip()
            if line != '' and not line.startswith(('#', 'svn+', 'git+')):
                requirements.append(line)
    return requirements


META = get_metadata('uwhoisd.py')


setup(
    name='uwhoisd',
    version=META['version'],
    description="Universal domain WHOIS proxy server.",
    long_description=read('README'),
    url='https://github.com/kgaughan/uwhoisd/',
    license='MIT',
    install_requires=read_requirements('requirements.txt'),
    py_modules=['uwhoisd'],
    zip_safe=True,

    entry_points={
        'console_scripts': [
            'uwhoisd = uwhoisd:main'
        ]
    },

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: System :: Networking',
    ],

    author=META['author'],
    author_email=META['email']
)
