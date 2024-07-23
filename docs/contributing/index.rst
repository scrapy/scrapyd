Contributing
============

.. important:: Read through the `Scrapy Contribution Docs <http://scrapy.readthedocs.org/en/latest/contributing.html>`__ for tips relating to writing patches, reporting bugs, and coding style.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api

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

Developer documentation
-----------------------

Scrapyd starts Scrapy processes. It runs ``scrapy crawl`` in the :ref:`launcher`, and ``scrapy list`` in the :ref:`schedule.json` (to check the spider exists), :ref:`addversion.json` (to return the number of spiders) and :ref:`listspiders.json` (to return the names of spiders) webservices.

Environment variables
~~~~~~~~~~~~~~~~~~~~~

Scrapyd uses environment variables to communicate between the Scrapyd process and the Scrapy processes that it starts.

SCRAPY_PROJECT
  The project to use. See ``scrapyd/runner.py``.
SCRAPYD_EGG_VERSION
  The version of the project, to be retrieved as an egg from :ref:`eggstorage` and activated.
SCRAPY_SETTINGS_MODULE
  The Python path to the `settings <https://docs.scrapy.org/en/latest/topics/settings.html#designating-the-settings>`__ module of the project.

  This is usually the module from the `entry points <https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`__ of the egg, but can be the module from the ``[settings]`` section of a :ref:`scrapy.cfg<config-settings>` file. See ``scrapyd/environ.py``.
