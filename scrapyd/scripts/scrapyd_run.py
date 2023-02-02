#!/usr/bin/env python

from os.path import dirname, join
from sys import argv

from twisted.scripts.twistd import run

import scrapyd
import pkgutil


def print_version():
    __version__ = pkgutil.get_data(__package__, '../VERSION').decode('ascii').strip()
    print(f'Scrapyd {__version__}')


def main():
    if len(argv) > 1 and set(argv[1:]) & set(['-v', '--version']):
        print_version()
        return
    argv[1:1] = ['-n', '-y', join(dirname(scrapyd.__file__), 'txapp.py')]
    run()


if __name__ == '__main__':
    main()
