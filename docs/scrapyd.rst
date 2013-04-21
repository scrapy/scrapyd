.. _topics-scrapyd:

Scrapy Service (scrapyd)
========================


Starting Scrapyd
================

Scrapyd is implemented using the standard `Twisted Application Framework`_. To
start the service, use the ``extras/scrapyd.tac`` file provided in the Scrapy
distribution, like this::

    twistd -ny extras/scrapyd.tac

That should get your Scrapyd started.

Or, if you want to start Scrapyd from inside a Scrapy project you can use the
:command:`server` command, like this::

    scrapy server

.. _topics-scrapyd-config:

Scrapyd Configuration file
==========================

Scrapyd searches for configuration files in the following locations, and parses
them in order with the latest ones taking more priority:

* ``/etc/scrapyd/scrapyd.conf`` (Unix)
* ``c:\scrapyd\scrapyd.conf`` (Windows)
* ``/etc/scrapyd/conf.d/*`` (in alphabetical order, Unix)
* ``scrapyd.conf``

The configuration file supports the following options (see default values in
the :ref:`example <topics-scrapyd-config-example>`).

http_port
---------

The TCP port where the HTTP JSON API will listen. Defaults to ``6800``.

bind_address
------------

The IP address where the HTTP JSON API will listen. Defaults to ``0.0.0.0`` (all)

max_proc
--------

The maximum number of concurrent Scrapy process that will be started. If unset
or ``0`` it will use the number of cpus available in the system mulitplied by
the value in ``max_proc_per_cpu`` option. Defaults to ``0``.

max_proc_per_cpu
----------------

The maximum number of concurrent Scrapy process that will be started per cpu.
Defaults to ``4``.

debug
-----

Whether debug mode is enabled. Defaults to ``off``. When debug mode is enabled
the full Python traceback will be returned (as plain text responses) when there
is an error processing a JSON API call.

eggs_dir
--------

The directory where the project eggs will be stored.

dbs_dir
-------

The directory where the project databases will be stored (this includes the
spider queues).

logs_dir
--------

The directory where the Scrapy logs will be stored. If you want to disable
storing logs set this option empty, like this::

    logs_dir =

.. _items_dir:

items_dir
---------

.. versionadded:: 0.15

The directory where the Scrapy items will be stored. If you want to disable
storing feeds of scraped items (perhaps, because you use a database or other
storage) set this option empty, like this::

    items_dir =

.. _jobs_to_keep:

jobs_to_keep
------------

.. versionadded:: 0.15

The number of finished jobs to keep per spider. Defaults to ``5``. This
includes logs and items.

This setting was named ``logs_to_keep`` in previous versions.

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

.. _topics-scrapyd-config-example:

Example configuration file
--------------------------

Here is an example configuration file with all the defaults:

.. literalinclude:: ../../scrapyd/default_scrapyd.conf

.. _topics-deploying:

.. _topics-scrapyd-webui:

Web Interface
=============

.. versionadded:: 0.11

Scrapyd comes with a minimal web interface (for monitoring running processes
and accessing logs) which can be accessed at http://localhost:6800/

