#!/usr/bin/env python

from setuptools import setup, find_packages
from buildkit import *


META = get_metadata('uwhoisd/__init__.py')


setup(
    name='uwhoisd',
    version=META['version'],
    description="Universal domain WHOIS proxy server.",
    long_description=read('README') + "\n\n" + read("ChangeLog"),
    url='https://github.com/kgaughan/uwhoisd/',
    license='MIT',
    packages=find_packages(exclude='tests'),
    zip_safe=True,
    install_requires=read_requirements('requirements.txt'),

    entry_points={
        'console_scripts': (
            'uwhoisd = uwhoisd:main',
        ),
    },

    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: System :: Networking',
    ),

    author=META['author'],
    author_email=META['email'],
)
