from os.path import join, dirname

with open(join(dirname(__file__), 'scrapyd-client/VERSION')) as f:
    version = f.read().strip()

setup_args = {
    'name': 'scrapyd-client',
    'version': version,
    'url': 'https://github.com/scrapy/scrapyd',
    'description': 'A client for scrapyd',
    'long_description': open('README.rst').read(),
    'author': 'Scrapy developers',
    'maintainer': 'Scrapy developers',
    'maintainer_email': 'info@scrapy.org',
    'license': 'BSD',
    'packages': ['scrapyd-client'],
    'scripts': ['scrapyd-client/scrapyd-deploy'],
    'include_package_data': True,
    'zip_safe': False,
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
