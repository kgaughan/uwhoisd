#!/usr/bin/env python

from setuptools import setup

setup(
    name='uwhoisd',
    version='0.0.3',
    description="Universal domain WHOIS proxy server.",
    long_description=open('README').read(),
    url='https://github.com/kgaughan/uwhoisd/',
    install_requires=[line.rstrip() for line in open('requirements.txt')],
    py_modules=['uwhoisd'],

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

    author='Keith Gaughan',
    author_email='k@stereochro.me',
)
