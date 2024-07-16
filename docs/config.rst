.. _config:

Configuration file
==================

Scrapyd searches for configuration files in the following locations, and parses
them in order with the latest one taking more priority:

* ``/etc/scrapyd/scrapyd.conf`` (Unix)
* ``c:\scrapyd\scrapyd.conf`` (Windows)
* ``/etc/scrapyd/conf.d/*`` (in alphabetical order, Unix)
* ``scrapyd.conf``
* ``~/.scrapyd.conf`` (users home directory)

The configuration file supports the options below (see default values in
the :ref:`example <config-example>`).

Environment variables
---------------------

.. versionadded:: 1.5.0

The following environment variables override corresponding options:

* ``SCRAPYD_BIND_ADDRESS`` (:ref:`bind_address`)
* ``SCRAPYD_HTTP_PORT`` (:ref:`http_port`)
* ``SCRAPYD_USERNAME`` (:ref:`username`)
* ``SCRAPYD_PASSWORD`` (:ref:`password`)

Application options
-------------------

.. _application:

application
~~~~~~~~~~~

The function that returns the Twisted Application to use.

If necessary, override this to fully control how Scrapyd works.

Default
  ``scrapyd.app.application``

.. seealso::

   `Twisted Application Framework <http://twistedmatrix.com/documents/current/core/howto/application.html>`__

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

     .. note::

        If ``sysctl`` sets ``net.ipv6.bindv6only`` to true (default false), then ``::0`` listens for IPv6 connections only.

.. _http_port:

http_port
~~~~~~~~~

The TCP port on which the :ref:`webui` and :doc:`api` listen for connections.

Default
  ``6800``
Options
  Any integer

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

poll_interval
~~~~~~~~~~~~~

The number of seconds to wait between checking whether the number of Scrapy processes that are running is less than the :ref:`max_proc` value.

Default
  ``5.0``
Options
   Any floating-point number

.. attention::

   It is not recommended to use a low interval like 0.1 when using the default :ref:`spiderqueue` value. Consider a custom queue based on `queuelib <https://github.com/scrapy/queuelib>`__.

.. _spiderqueue:

spiderqueue
~~~~~~~~~~~

The class that stores job queues.

Default
  ``scrapyd.spiderqueue.SqliteSpiderQueue``
Options
  -  ``scrapyd.spiderqueue.SqliteSpiderQueue`` stores spider queues in SQLite databases named after each project, in the :ref:`dbs_dir` directory
  -  Implement your own, using the ``ISpiderQueue`` interface
Also used by
  -  :ref:`addversion.json` webservice, to create a queue if the project is new
  -  :ref:`schedule.json` webservice, to add a pending job
  -  :ref:`cancel.json` webservice, to remove a pending job
  -  :ref:`listjobs.json` webservice, to list the pending jobs
  -  :ref:`daemonstatus.json` webservice, to count the pending jobs
  -  :ref:`webui`, to list the pending jobs and, if queues are transient, to create the queues per project at startup

Launcher options
----------------

launcher
~~~~~~~~

The class that starts Scrapy processes.

Default
  ``scrapyd.launcher.Launcher``

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

.. _items_dir:

items_dir
~~~~~~~~~

The directory in which to write Scrapy items.

If this option is non-empty, the `FEEDS <https://docs.scrapy.org/en/latest/topics/feed-exports.html#std-setting-FEEDS>`__ Scrapy setting is set as follows, resulting in feeds being written to the specified directory as JSON lines:

.. code-block:: json

   {"value from items_dir": {"format": "jsonlines"}}

Default
  ``""`` (empty), because it is recommended to instead use either:

   -  `Feed exports <https://docs.scrapy.org/en/latest/topics/feed-exports.html>`__, by setting the ``FEEDS`` Scrapy setting in your Scrapy project. See the full list of `storage backends <https://docs.scrapy.org/en/latest/topics/feed-exports.html#storages>`__.
   -  `Item pipeline <https://docs.scrapy.org/en/latest/topics/item-pipeline.html>`__, to store the scraped items in a database. See the `MongoDB example <https://docs.scrapy.org/en/latest/topics/item-pipeline.html#write-items-to-mongodb>`__, which can be adapted to another database.
Also used by
  :ref:`webui`, to link to item feeds

.. _jobs_to_keep:

jobs_to_keep
~~~~~~~~~~~~

The number of finished jobs per spider, for which to keep log files in the :ref:`logs_dir` directory and item feeds in the :ref:`items_dir` directory.

To "disable" this feature, set this to an arbitrarily large value. For example, on a 64-bit system:

.. code-block:: ini

   jobs_to_keep = 9223372036854775807

Default
  ``5``

runner
~~~~~~

The Python `script <https://docs.python.org/3/tutorial/modules.html#executing-modules-as-scripts>`__ to run Scrapy's `CLI <https://docs.scrapy.org/en/latest/topics/commands.html>`__.

If necessary, override this to fully control how the Scrapy CLI is called.

Default
  ``scrapyd.runner``
Also used by
  :ref:`listspiders.json` webservice, to run Scrapy's `list <https://docs.scrapy.org/en/latest/topics/commands.html#list>`__ command

Web UI and API options
----------------------

.. _webroot:

webroot
~~~~~~~

The class that defines the :ref:`webui` and :doc:`api`, as a Twisted Resource.

If necessary, override this to fully control how the web UI and API work.

Default
  ``scrapyd.website.Root``

.. _prefix_header:

prefix_header
~~~~~~~~~~~~~

.. versionadded:: 1.4.2

The header for the base path of the original request.

The header is relevant only if Scrapyd is running behind a reverse proxy, and if the public URL contains a base path, before the Scrapyd API path components.
A base path must have a leading slash and no trailing slash, e.g. ``/base/path``.

Default
  ``x-forwarded-prefix``

node_name
~~~~~~~~~

.. versionadded:: 1.1.0

The node name, which appears in :doc:`api` responses.

Default
  ``socket.gethostname()``

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

The class that stores project eggs.

Default
  ``scrapyd.eggstorage.FilesystemEggStorage``
Options
  -  ``scrapyd.eggstorage.FilesystemEggStorage`` writes eggs in the :ref:`eggs_dir` directory
  -  Implement your own, using the ``IEggStorage`` interface: for example, to store eggs remotely

.. _eggs_dir:

eggs_dir
~~~~~~~~

The directory in which to write project eggs.

Default
  ``eggs``

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
  -  Implement your own, using the ``IJobStorage`` interface

.. seealso::

   :ref:`finished_to_keep`

.. _finished_to_keep:

finished_to_keep
~~~~~~~~~~~~~~~~

The number of finished jobs, for which to keep metadata in the :ref:`jobstorage` backend.

Finished jobs are accessed via the :ref:`webui` and :ref:`listjobs.json` webservice.

Default
  ``100``

Directories
-----------

.. _dbs_dir:

dbs_dir
~~~~~~~

The directory in which to write SQLite databases.

Default
  ``dbs``
Used by
  -  :ref:`spiderqueue` (``scrapyd.spiderqueue.SqliteSpiderQueue``)
  -  :ref:`jobstorage` (``scrapyd.jobstorage.SqliteJobStorage``)

.. _config-services:

Services
--------

Normally, you can leave the ``[services]`` section from the :ref:`example <config-example>` as-is.

If you want to add a webservice (endpoint), add another line, like:

.. code-block:: ini
   :emphasize-lines: 2

   [services]
   mywebservice.json   = amodule.anothermodule.MyWebService
   schedule.json     = scrapyd.webservice.Schedule
   ...

You can use the webservices in `webservice.py <https://github.com/scrapy/scrapyd/blob/master/scrapyd/webservice.py>`__ as inspiration.

.. _config-example:

Example configuration file
--------------------------

Here is an example configuration file with all the defaults:

.. literalinclude:: ../scrapyd/default_scrapyd.conf
