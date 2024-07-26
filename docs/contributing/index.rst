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

   pip install -e .[test,docs]

Developer documentation
-----------------------

Configuration
~~~~~~~~~~~~~

Pass the ``config`` object to a class' ``__init__`` method, but don't store it on the instance (:issue:`526`).

Processes
~~~~~~~~~

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

Jobs
~~~~

A **pending job** is a ``dict`` object (referred to as a "message"), accessible via an :py:interface:`~scrapyd.interfaces.ISpiderQueue`'s :meth:`~scrapyd.interfaces.ISpiderQueue.pop` or :meth:`~scrapyd.interfaces.ISpiderQueue.list` methods.

.. note:: The short-lived message returned by :py:interface:`~scrapyd.interfaces.IPoller`'s :meth:`~scrapyd.interfaces.IPoller.poll` method is also referred to as a "message".

-  The :ref:`schedule.json` webservice calls :py:interface:`~scrapyd.interfaces.ISpiderScheduler`'s :meth:`~scrapyd.interfaces.ISpiderScheduler.schedule` method. The ``SpiderScheduler`` implementation of :meth:`~scrapyd.interfaces.ISpiderScheduler.schedule` adds the message to the project's :py:interface:`~scrapyd.interfaces.ISpiderQueue`.
-  The default :ref:`application` sets a `TimerService <https://docs.twisted.org/en/stable/api/twisted.application.internet.TimerService.html>`__ to call :py:interface:`~scrapyd.interfaces.IPoller`'s :meth:`~scrapyd.interfaces.IPoller.poll` method, at :ref:`poll_interval`.
-  :py:interface:`~scrapyd.interfaces.IPoller` has a :attr:`~scrapyd.interfaces.IPoller.queues` attribute, that implements a ``__getitem__`` method to get a project's :py:interface:`~scrapyd.interfaces.ISpiderQueue` by project name.
-  The ``QueuePoller`` implementation of :meth:`~scrapyd.interfaces.IPoller.poll` calls a project's :py:interface:`~scrapyd.interfaces.ISpiderQueue`'s :meth:`~scrapyd.interfaces.ISpiderQueue.pop` method, adds a ``_project`` key to the message and renames the ``name`` key to ``_spider``, and fires a callback.
-  The ``Launcher`` service had added the callback to the `Deferred <https://docs.twisted.org/en/stable/core/howto/defer.html>`__, which had been returned by :py:interface:`~scrapyd.interfaces.IPoller`'s :meth:`~scrapyd.interfaces.IPoller.next` method.
-  The ``Launcher`` service adapts the message to instantiate a ``ScrapyProcessProtocol`` (`ProcessProtocol <https://docs.twisted.org/en/stable/api/twisted.internet.protocol.ProcessProtocol.html>`__) object, adds a callback, and `spawns a process <https://docs.twisted.org/en/stable/core/howto/process.html>`__.

A **running job** is a ``ScrapyProcessProtocol`` object, accessible via ``Launcher.processes`` (a ``dict``), in which each key is a slot's number (an ``int``).

-  ``Launcher`` has a ``finished`` attribute, which is an :py:interface:`~scrapyd.interfaces.IJobStorage`.
-  When the process ends, the callback fires. The ``Launcher`` service calls :py:interface:`~scrapyd.interfaces.IJobStorage`'s :meth:`~scrapyd.interfaces.IJobStorage.add` method, passing the ``ScrapyProcessProtocol`` as input.

A **finished job** is an object with the attributes ``project``, ``spider``, ``job``, ``start_time`` and ``end_time``, accessible via an :py:interface:`~scrapyd.interfaces.IJobStorage`'s :meth:`~scrapyd.interfaces.IJobStorage.list` or :meth:`~scrapyd.interfaces.IJobStorage.__iter__` methods.

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * - Concept
     - ISpiderQueue
     - IPoller
     - ScrapyProcessProtocol
     - IJobStorage
   * - Project
     - *not specified*
     - _project
     - project
     - project
   * - Spider
     - name
     - _spider
     - spider
     - spider
   * - Job ID
     - _job
     - _job
     - job
     - job
   * - Egg version
     - _version
     - _version
     - ✗
     - ✗
   * - Scrapy settings
     - settings
     - settings
     - args (``-s k=v``)
     - ✗
   * - Spider arguments
     - *remaining keys*
     - *remaining keys*
     - args (``-a k=v``)
     - ✗
   * - Environment variables
     - ✗
     - ✗
     - env
     - ✗
   * - Process ID
     - ✗
     - ✗
     - pid
     - ✗
   * - Start time
     - ✗
     - ✗
     - start_time
     - start_time
   * - End time
     - ✗
     - ✗
     - end_time
     - end_time
