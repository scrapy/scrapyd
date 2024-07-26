=============
Configuration
=============

.. _config-default:

Default configuration
=====================

Scrapyd always loads this configuration file, which can be overridden by :ref:`config-sources`:

.. literalinclude:: ../scrapyd/default_scrapyd.conf

.. _config-sources:

Configuration sources
=====================

Scrapyd reads these configuration files in this order. Values in later files take priority.

#. ``c:\scrapyd\scrapyd.conf``
#. ``/etc/scrapyd/scrapyd.conf``
#. ``/etc/scrapyd/conf.d/*`` in alphabetical order
#. ``scrapyd.conf`` in the current directory
#. ``~/.scrapyd.conf`` in the home directory of the user that invoked the ``scrapyd`` command
#. the closest ``scrapy.cfg`` file, starting in the current directory and traversing upward

.. _config-envvars:

Environment variables
=====================

.. versionadded:: 1.5.0

These environment variables override corresponding options:

* ``SCRAPYD_BIND_ADDRESS`` (:ref:`bind_address`)
* ``SCRAPYD_HTTP_PORT`` (:ref:`http_port`)
* ``SCRAPYD_USERNAME`` (:ref:`username`)
* ``SCRAPYD_PASSWORD`` (:ref:`password`)
* ``SCRAPYD_UNIX_SOCKET_PATH`` (:ref:`unix_socket_path`)

scrapyd section
===============

Application options
-------------------

.. _application:

application
~~~~~~~~~~~

The function that returns the Twisted Application to use.

If necessary, override this to fully control how Scrapyd works.

Default
  ``scrapyd.app.application``
Options
  Any Twisted `Application <https://docs.twisted.org/en/stable/core/howto/application.html>`__

.. _bind_address:

bind_address
~~~~~~~~~~~~

The IP address on which the :ref:`webui` and :doc:`api` listen for connections.

Default
  ``127.0.0.1``
Options
  Any IP address, including:

  -  ``127.0.0.1`` to listen for local IPv4 connections only
  -  ``0.0.0.0`` to listen for all IPv4 connections
  -  ``::0`` to listen for all IPv4 and IPv6 connections

     .. note:: If ``sysctl`` sets ``net.ipv6.bindv6only`` to true (default false), then ``::0`` listens for IPv6 connections only.

.. _http_port:

http_port
~~~~~~~~~

The TCP port on which the :ref:`webui` and :doc:`api` listen for connections.

Default
  ``6800``
Options
  Any integer

.. _unix_socket_path:

unix_socket_path
----------------

.. versionadded:: 1.5.0

The filesystem path of the Unix socket on which the :ref:`webui` and :doc:`api` listen for connections.

For example:

.. code-block:: ini

   unix_socket_path = /var/run/scrapyd/web.socket

The file's mode is set to 660 (owner and group, read and write) to control access to Scrapyd.

.. attention::

   If :ref:`bind_address` and :ref:`http_port` are set, a TCP server will start, in addition to the Unix server. To disable the TCP server, set ``bind_address`` to empty:

   .. code-block:: ini

      bind_address =

.. _username:

username
~~~~~~~~

.. versionadded:: 1.3.0

Enable basic authentication by setting this and :ref:`password` to non-empty values.

Default
  ``""`` (empty)

.. _password:

password
~~~~~~~~

.. versionadded:: 1.3.0

Enable basic authentication by setting this and :ref:`username` to non-empty values.

Default
  ``""`` (empty)

.. _spiderqueue:

spiderqueue
~~~~~~~~~~~

.. versionadded:: 1.4.2

The class that stores pending jobs.

Default
  ``scrapyd.spiderqueue.SqliteSpiderQueue``
Options
  -  ``scrapyd.spiderqueue.SqliteSpiderQueue`` stores spider queues in SQLite databases named after each project, in the :ref:`dbs_dir` directory
  -  Implement your own, using the :py:interface:`~scrapyd.interfaces.ISpiderQueue` interface
Also used by
  -  :ref:`addversion.json` webservice, to create a queue if the project is new
  -  :ref:`schedule.json` webservice, to add a pending job
  -  :ref:`cancel.json` webservice, to remove a pending job
  -  :ref:`listjobs.json` webservice, to list the pending jobs
  -  :ref:`daemonstatus.json` webservice, to count the pending jobs
  -  :ref:`webui`, to list the pending jobs and, if queues are transient, to create the queues per project at startup

.. Community PostgreSQL and RabbitMQ queues: https://github.com/scrapy/scrapyd/pull/140/files#diff-c479470812a00776da54c3cefc15bb5bb244b4056996ae972f4daba7f6ec5bd5

Poller options
--------------

.. _poller:

poller
~~~~~~

.. versionadded:: 1.5.0

The class that tracks capacity for new jobs, and starts jobs when ready.

Default
  ``scrapyd.poller.QueuePoller``
Options
  -  ``scrapyd.poller.QueuePoller``. When using the default :ref:`application` and :ref:`launcher` values:

    -  The launcher adds :ref:`max_proc` capacity at startup, and one capacity each time a Scrapy process ends.
    -  The :ref:`application` starts a timer so that, every :ref:`poll_interval` seconds, jobs start if there's capacity: that is, if the number of Scrapy processes that are running is less than the :ref:`max_proc` value.

  -  Implement your own, using the :py:interface:`~scrapyd.interfaces.IPoller` interface

.. _poll_interval:

poll_interval
~~~~~~~~~~~~~

The number of seconds between capacity checks.

Default
  ``5.0``
Options
   Any floating-point number

.. _config-launcher:

Launcher options
----------------

.. _launcher:

launcher
~~~~~~~~

The class that starts Scrapy processes.

Default
  ``scrapyd.launcher.Launcher``
Options
  Any Twisted `Service <https://docs.twisted.org/en/stable/api/twisted.application.service.Service.html>`__

.. _max_proc:

max_proc
~~~~~~~~

The maximum number of Scrapy processes to run concurrently.

Default
  ``0``
Options
  Any non-negative integer, including:

  -  ``0`` to use :ref:`max_proc_per_cpu` multiplied by the number of CPUs

.. _max_proc_per_cpu:

max_proc_per_cpu
~~~~~~~~~~~~~~~~

See :ref:`max_proc`.

Default
  ``4``

.. _logs_dir:

logs_dir
~~~~~~~~

The directory in which to write Scrapy logs.

A log file is written to ``{logs_dir}/{project}/{spider}/{job}.log``.

To disable log storage, set this option to empty:

.. code-block:: ini

   logs_dir =

To log messages to a remote service, you can, for example, reconfigure Scrapy's logger from your Scrapy project:

.. code-block:: python

   import logging
   import logstash

   logger = logging.getLogger("scrapy")
   logger.handlers.clear()
   logger.addHandler(logstash.LogstashHandler("https://user:pass@id.us-east-1.aws.found.io", 5959, version=1))

Default
  ``logs``
Also used by
  :ref:`webui`, to link to log files

.. attention:: Each ``*_dir`` setting must point to a different directory.

.. _items_dir:

items_dir
~~~~~~~~~

The directory in which to write Scrapy items.

An item feed is written to ``{items_dir}/{project}/{spider}/{job}.jl``.

If this option is non-empty, the `FEEDS <https://docs.scrapy.org/en/latest/topics/feed-exports.html#std-setting-FEEDS>`__ Scrapy setting is set as follows, resulting in items being written to the above path as JSON lines:

.. code-block:: json

   {"file:///path/to/items_dir/project/spider/job.jl": {"format": "jsonlines"}}

Default
  ``""`` (empty), because it is recommended to instead use either:

   -  `Feed exports <https://docs.scrapy.org/en/latest/topics/feed-exports.html>`__, by setting the ``FEEDS`` Scrapy setting in your Scrapy project. See the full list of `storage backends <https://docs.scrapy.org/en/latest/topics/feed-exports.html#storages>`__.
   -  `Item pipeline <https://docs.scrapy.org/en/latest/topics/item-pipeline.html>`__, to store the scraped items in a database. See the `MongoDB example <https://docs.scrapy.org/en/latest/topics/item-pipeline.html#write-items-to-mongodb>`__, which can be adapted to another database.
Also used by
  :ref:`webui`, to link to item feeds

.. attention:: Each ``*_dir`` setting must point to a different directory.

.. _jobs_to_keep:

jobs_to_keep
~~~~~~~~~~~~

The number of finished jobs per spider, for which to keep the most recent log files in the :ref:`logs_dir` directory and item feeds in the :ref:`items_dir` directory.

To "disable" this feature, set this to an arbitrarily large value. For example, on a 64-bit system:

.. code-block:: ini

   jobs_to_keep = 9223372036854775807

.. warning::

   Scrapyd deletes old files in these directories, regardless of origin.

Default
  ``5``

.. _runner:

runner
~~~~~~

The Python script to run Scrapy's `CLI <https://docs.scrapy.org/en/latest/topics/commands.html>`__.

If necessary, override this to fully control how the Scrapy CLI is called.

Default
  ``scrapyd.runner``
Options
  Any Python `script <https://docs.python.org/3/tutorial/modules.html#executing-modules-as-scripts>`__
Also used by
  :ref:`listspiders.json` webservice, to run Scrapy's `list <https://docs.scrapy.org/en/latest/topics/commands.html#list>`__ command

Web UI and API options
----------------------

.. _webroot:

webroot
~~~~~~~

.. versionadded:: 1.2.0

The class that defines the :ref:`webui` and :doc:`api`, as a Twisted Resource.

If necessary, override this to fully control how the web UI and API work.

Default
  ``scrapyd.website.Root``
Options
  Any Twisted `Resource <https://docs.twisted.org/en/stable/web/howto/using-twistedweb.html#resource-objects>`__

.. _prefix_header:

prefix_header
~~~~~~~~~~~~~

.. versionadded:: 1.4.2

The header for the base path of the original request.

The header is relevant only if Scrapyd is running behind a reverse proxy, and if the public URL contains a base path, before the Scrapyd API path components.
A base path must have a leading slash and no trailing slash, e.g. ``/base/path``.

Default
  ``x-forwarded-prefix``

.. _node_name:

node_name
~~~~~~~~~

.. versionadded:: 1.1.0

The node name, which appears in :doc:`api` responses.

Default
  ``socket.gethostname()``

.. _debug:

debug
~~~~~

Whether debug mode is enabled.

If enabled, a Python traceback is returned (as a plain-text response) when the :doc:`api` errors.

Default
  ``off``

Egg storage options
-------------------

.. _eggstorage:

eggstorage
~~~~~~~~~~

.. versionadded:: 1.3.0

The class that stores project eggs.

Default
  ``scrapyd.eggstorage.FilesystemEggStorage``
Options
  -  ``scrapyd.eggstorage.FilesystemEggStorage`` writes eggs in the :ref:`eggs_dir` directory

     .. note:: Eggs are named after the ``version``, replacing characters other than ``A-Za-z0-9_-`` with underscores. Therefore, if you frequently use non-word, non-hyphen characters, the eggs for different versions can collide.
  -  Implement your own, using the :py:interface:`~scrapyd.interfaces.IEggStorage` interface: for example, to store eggs remotely

.. _eggs_dir:

eggs_dir
~~~~~~~~

The directory in which to write project eggs.

Default
  ``eggs``

.. attention:: Each ``*_dir`` setting must point to a different directory.

Job storage options
-------------------

.. _jobstorage:

jobstorage
~~~~~~~~~~

.. versionadded:: 1.3.0

The class that stores finished jobs.

Default
  ``scrapyd.jobstorage.MemoryJobStorage``
Options
  -  ``scrapyd.jobstorage.MemoryJobStorage`` stores jobs in memory, such that jobs are lost when the Scrapyd process ends
  -  ``scrapyd.jobstorage.SqliteJobStorage`` stores jobs in a SQLite database named ``jobs.db``, in the :ref:`dbs_dir` directory
  -  Implement your own, using the :py:interface:`~scrapyd.interfaces.IJobStorage` interface

.. _finished_to_keep:

finished_to_keep
~~~~~~~~~~~~~~~~

The number of finished jobs, for which to keep metadata in the :ref:`jobstorage` backend.

Finished jobs are accessed via the :ref:`webui` and :ref:`listjobs.json` webservice.

Default
  ``100``
Options
  Any non-negative integer, including:

  -  ``0`` to keep all finished jobs

Directory options
-----------------

.. _dbs_dir:

dbs_dir
~~~~~~~

The directory in which to write SQLite databases.

Default
  ``dbs``
Options
  Any relative or absolute path, or `:memory: <https://docs.python.org/3/library/sqlite3.html#sqlite3.connect>`__
Used by
  -  :ref:`spiderqueue` (``scrapyd.spiderqueue.SqliteSpiderQueue``)
  -  :ref:`jobstorage` (``scrapyd.jobstorage.SqliteJobStorage``)

.. attention:: Each ``*_dir`` setting must point to a different directory.

.. _config-services:

services section
================

If you want to add a webservice (endpoint), add, for example:

.. code-block:: ini

   [services]
   mywebservice.json = amodule.anothermodule.MyWebService

You can use code for webservices in `webservice.py <https://github.com/scrapy/scrapyd/blob/master/scrapyd/webservice.py>`__ as inspiration.

To remove a :ref:`default webservice<config-default>`, set it to empty:

.. code-block:: ini

   [services]
   daemonstatus.json =

.. _config-settings:

settings section (scrapy.cfg)
=============================

Project code is usually stored in a `Python egg <https://setuptools.pypa.io/en/latest/deprecated/python_eggs.html>`__ and uploaded to Scrapyd via the :ref:`addversion.json` webservice.

Alternatively, you can invoke Scrapyd within a Scrapy project: that is, you can run the ``scrapyd`` command from a directory containing a ``scrapy.cfg`` file (or from a directory with any parent directory containing a ``scrapy.cfg`` file).

As described in `Scrapy's documentation <https://docs.scrapy.org/en/latest/topics/commands.html#sharing-the-root-directory-between-projects>`__, the ``scrapy.cfg`` file contains a ``[settings]`` section, which can describe many Scrapy projects. By default, it is:

.. code-block:: ini

   [settings]
   default = projectname.settings
