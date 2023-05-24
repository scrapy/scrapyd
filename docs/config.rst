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

The configuration file supports the following options (see default values in
the :ref:`example <config-example>`).

http_port
---------

The TCP port where the HTTP JSON API will listen. Defaults to ``6800``.

bind_address
------------

The IP address where the website and json webservices will listen.
Defaults to ``127.0.0.1`` (localhost)

username
--------

.. versionadded:: 1.3

Set both ``username`` and ``password`` to non-empty to enable basic authentication.

password
--------

.. versionadded:: 1.3

See the ``username`` option above.

.. _max_proc:

max_proc
--------

The maximum number of concurrent Scrapy process that will be started. If unset
or ``0`` it will use the number of cpus available in the system multiplied by
the value in ``max_proc_per_cpu`` option. Defaults to ``0``.

.. _max_proc_per_cpu:

max_proc_per_cpu
----------------

The maximum number of concurrent Scrapy process that will be started per cpu.
Defaults to ``4``.

debug
-----

Whether debug mode is enabled. Defaults to ``off``. When debug mode is enabled
the full Python traceback will be returned (as plain text responses) when there
is an error processing a JSON API call.

.. _eggs_dir:

eggs_dir
--------

The directory where the project eggs will be stored.

.. seealso::

   :ref:`eggstorage`

dbs_dir
-------

The directory where the project databases will be stored (this includes the
spider queues).

logs_dir
--------

The directory where the Scrapy logs will be stored.

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

.. _items_dir:

items_dir
---------

.. versionadded:: 0.15

The directory where the Scrapy items will be stored.

This option is disabled by default. It is recommended to either:

-  Use `feed exports <https://docs.scrapy.org/en/latest/topics/feed-exports.html>`__, by setting the ``FEEDS`` Scrapy setting in your Scrapy project. See the full list of `storage backends <https://docs.scrapy.org/en/latest/topics/feed-exports.html#storages>`__.
-  Use the `item pipeline <https://docs.scrapy.org/en/latest/topics/item-pipeline.html>`__, to store the scraped items in a database. See the `MongoDB example <https://docs.scrapy.org/en/latest/topics/item-pipeline.html#write-items-to-mongodb>`__, which can be adapted to another database.

If this option is non-empty, the `FEEDS <https://docs.scrapy.org/en/latest/topics/feed-exports.html#std-setting-FEEDS>`__ Scrapy setting is set as follows, resulting in feeds being stored in the specified directory as JSON lines.

.. code-block:: json

   {"value from items_dir": {"format": "jsonlines"}}

.. _jobs_to_keep:

jobs_to_keep
------------

.. versionadded:: 0.15

The number of finished jobs to keep per spider.
Defaults to ``5``.
This refers to logs and items.

This setting was named ``logs_to_keep`` in previous versions.

.. _finished_to_keep:

finished_to_keep
----------------

.. versionadded:: 0.14

The number of finished processes to keep in the launcher.
Defaults to ``100``.
This only reflects on the website /jobs endpoint and relevant json webservices.

poll_interval
-------------

The interval used to poll queues, in seconds.
Defaults to ``5.0``.
Can be a float, such as ``0.2``

.. _prefix_header:

prefix_header
-------------

.. versionadded:: 1.4.2

The header for the base path of the original request.
A base path must have a leading slash and no trailing slash, e.g. ``/base/path``.
The header is relevant only if Scrapyd is running behind a reverse proxy, and if the public URL contains a base path, before the Scrapyd API path components.
Defaults to ``x-forwarded-prefix``.

runner
------

The module that will be used for launching sub-processes. You can customize the
Scrapy processes launched from Scrapyd by using your own module.

application
-----------

A function that returns the (Twisted) Application object to use. This can be
used if you want to extend Scrapyd by adding and removing your own components
and services.

For more info see `Twisted Application Framework`_

.. _spiderqueue:

spiderqueue
-----------

The scheduler enqueues crawls in per-project spider queues, for the poller to pick.
You can define a custom spider queue class that implements the ISpiderQueue interface.

Defaults to ``scrapyd.spiderqueue.SqliteSpiderQueue``.

.. _webroot:

webroot
-------

A twisted web resource that represents the interface to scrapyd.
Scrapyd includes an interface with a website to provide simple monitoring
and access to the application's webresources.
This setting must provide the root class of the twisted web resource.

jobstorage
----------

.. versionadded:: 1.3

A class that stores finished jobs. There are 2 implementations provided:

* ``scrapyd.jobstorage.MemoryJobStorage`` (default) jobs are stored in memory and lost when the daemon is restarted
* ``scrapyd.jobstorage.SqliteJobStorage`` jobs are persisted in a Sqlite database in ``dbs_dir``

If another backend is needed, one can implement its own class by implementing the IJobStorage
interface.

.. _eggstorage:

eggstorage
----------

A class that stores project eggs, implementing the ``IEggStorage`` interface.

The default value is ``scrapyd.eggstorage.FilesystemEggStorage``.
This implementation stores eggs in the directory specified by the :ref:`eggs_dir` setting.

You can implement your own egg storage: for example, to store eggs remotely.

node_name
---------

.. versionadded:: 1.1

The node name for each node to something like the display hostname. Defaults to ``${socket.gethostname()}``.

.. _config-example:

Example configuration file
--------------------------

Here is an example configuration file with all the defaults:

.. literalinclude:: ../scrapyd/default_scrapyd.conf
.. _Twisted Application Framework: http://twistedmatrix.com/documents/current/core/howto/application.html
