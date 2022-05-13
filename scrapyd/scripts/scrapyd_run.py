#!/usr/bin/env python

from os.path import dirname, join
from sys import argv

from twisted.scripts.twistd import run

import scrapyd


def main():
    argv[1:1] = ['-n', '-y', join(dirname(scrapyd.__file__), 'txapp.py')]
    run()


if __name__ == '__main__':
    main()
