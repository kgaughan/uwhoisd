#!/usr/bin/env python

from __future__ import with_statement

from setuptools import setup
from buildkit import *


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
    author_email=META['email'],
)
