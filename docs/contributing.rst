.. _contributing:

Contributing
============

.. important::

    Read through the `Scrapy Contribution Docs <http://scrapy.readthedocs.org/en/latest/contributing.html>`__ for tips relating to writing patches, reporting bugs, and project coding style

These docs describe how to setup and contribute to Scrapyd.

Reporting issues & bugs
-----------------------

Issues should be reported to the Scrapyd project `issue tracker <https://github.com/scrapy/scrapyd/issues>`__ on GitHub.

Tests
-----

Tests are implemented using the `Twisted unit-testing framework <http://twistedmatrix.com/documents/current/core/development/policy/test-standard.html>`__. Scrapyd uses ``trial`` as the test running application.

Running tests
-------------

To run all tests go to the root directory of the Scrapyd source code and run:

    ``trial tests``

To run a specific test (say ``tests/test_poller.py``) use:

    ``trial tests.test_poller``


Writing tests
-------------

All functionality (including new features and bug fixes) should include a test
case to check that it works as expected, so please include tests for your
patches if you want them to get accepted sooner.

Scrapyd uses unit-tests, which are located in the `tests <https://github.com/scrapy/scrapyd/tree/master/tests>`__ directory.
Their module name typically resembles the full path of the module they're
testing. For example, the scheduler code is in::

    scrapyd.scheduler

And their unit-tests are in::

    tests/test_scheduler.py

Installing locally
------------------

To install a locally edited version of Scrapyd onto the system to use and test, inside the project root run:

    ``pip install -e .``
