import os
from subprocess import Popen, PIPE

if os.environ.get('SCRAPY_VERSION_FROM_GIT'):
    v = Popen("git describe", shell=True, stdout=PIPE).communicate()[0]
    with open('scrapyd/VERSION', 'w+') as f:
        f.write(v.strip())

with open(os.path.join(os.path.dirname(__file__), 'scrapyd/VERSION')) as f:
    version = f.read().strip()

setup_args = {
    'name': 'Scrapyd',
    'version': version,
    'url': 'https://github.com/scrapy/scrapyd',
    'description': 'A service for running Scrapy spiders, with an HTTP API',
    'long_description': open('README.rst').read(),
    'author': 'Scrapy developers',
    'maintainer': 'Scrapy developers',
    'maintainer_email': 'info@scrapy.org',
    'license': 'BSD',
    'packages': ['scrapyd'],
    'scripts': ['bin/scrapyd'],
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Topic :: Internet :: WWW/HTTP',
    ],
}

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
else:
    setup_args['install_requires'] = ['Twisted>=8.0', 'Scrapy>=0.17']

setup(**setup_args)
