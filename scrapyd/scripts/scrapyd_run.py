#!/usr/bin/env python

import pkgutil
import sys
from os.path import dirname, join

from twisted.scripts.twistd import run

import scrapyd


def main():
    if len(sys.argv) > 1 and '-v' in sys.argv[1:] or '--version' in sys.argv[1:]:
        __version__ = pkgutil.get_data(__package__, '../VERSION').decode('ascii').strip()
        print(f'Scrapyd {__version__}')
    else:
        sys.argv[1:1] = ['-n', '-y', join(dirname(scrapyd.__file__), 'txapp.py')]
        run()


if __name__ == '__main__':
    main()
