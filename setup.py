import os.path

from setuptools import setup

with open("README.rst") as f:
    long_description = f.read()

with open(os.path.join(os.path.dirname(__file__), "scrapyd", "VERSION")) as f:
    version = f.read().strip()

setup(
    name="scrapyd",
    version=version,
    author="Scrapy developers",
    author_email="info@scrapy.org",
    url="https://github.com/scrapy/scrapyd",
    description="A service for running Scrapy spiders, with an HTTP API",
    license="BSD",
    packages=["scrapyd"],
    long_description=long_description,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    # The scrapyd.__main__ module requires the txapp.py file to be decompressed. #49
    zip_safe=False,
    install_requires=[
        "packaging",
        "pywin32;platform_system=='Windows'",
        "scrapy>=2.0.0",
        "setuptools",
        "twisted>=17.9",
        "w3lib",
        "zope.interface",
    ],
    extras_require={
        "test": [
            "coveralls",
            "py-html-checker",
            "pytest",
            "pytest-cov",
            "pytest-twisted",
            "requests",
            "twisted>=19.7",  # twisted.logger.capturedLogs
        ],
        "docs": [
            "furo",
            "sphinx",
            "sphinx-autobuild",
            "sphinxcontrib-zopeext",
        ],
    },
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: No Input/Output (Daemon)",
        "Topic :: Internet :: WWW/HTTP",
    ],
    entry_points={"console_scripts": ["scrapyd = scrapyd.__main__:main"]},
)
