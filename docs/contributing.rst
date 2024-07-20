Contributing
============

.. important:: Read through the `Scrapy Contribution Docs <http://scrapy.readthedocs.org/en/latest/contributing.html>`__ for tips relating to writing patches, reporting bugs, and coding style.

Issues and bugs
---------------

Report on `GitHub <https://github.com/scrapy/scrapyd/issues>`__.

Tests
-----

Include tests in your pull requests.

To run unit tests:

.. code-block:: shell

   pytest tests

To run integration tests:

.. code-block:: shell

   printf "[scrapyd]\nusername = hello12345\npassword = 67890world\n" > scrapyd.conf
   mkdir logs
   scrapyd &
   pytest integration_tests

Installation
------------

To install an editable version for development, clone the repository, change to its directory, and run:

.. code-block:: shell

   pip install -e .
