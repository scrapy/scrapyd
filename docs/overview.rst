========
Overview
========

Projects and versions
=====================

Scrapyd can manage multiple projects and each project can have multiple
versions uploaded, but only the latest one will be used for launching new
spiders.

A common (and useful) convention to use for the version name is the revision
number of the version control tool you're using to track your Scrapy project
code. For example: ``r23``. The versions are not compared alphabetically but
using a smarter algorithm (the same `distutils`_ uses) so ``r10`` compares
greater to ``r9``, for example.

How Scrapyd works
=================

Scrapyd is an application (typically run as a daemon) that listens to requests
for spiders to run and spawns a process for each one, which basically
executes::

    scrapy crawl myspider

Scrapyd also runs multiple processes in parallel, allocating them in a fixed
number of slots given by the :ref:`max_proc` and :ref:`max_proc_per_cpu` options,
starting as many processes as possible to handle the load.

In addition to dispatching and managing processes, Scrapyd provides a
:ref:`JSON web service <api>` to upload new project versions
(as eggs) and schedule spiders. This feature is optional and can be disabled if
you want to implement your own custom Scrapyd. The components are pluggable and
can be changed, if you're familiar with the `Twisted Application Framework`_
which Scrapyd is implemented in.

Starting from 0.11, Scrapyd also provides a minimal :ref:`web interface
<webui>`.

Starting Scrapyd
================

To start the service, use the ``scrapyd`` command provided in the Scrapy
distribution::

    scrapyd

That should get your Scrapyd started.

Scheduling a spider run
=======================

To schedule a spider run::

    $ curl http://localhost:6800/schedule.json -d project=myproject -d spider=spider2
    {"status": "ok", "jobid": "26d1b1a6d6f111e0be5c001e648c57f8"}

For more resources see: :ref:`api` for more available resources.

.. _webui:

Web Interface
=============

Scrapyd comes with a minimal web interface (for monitoring running processes
and accessing logs) which can be accessed at http://localhost:6800/

Alternatively, you can use `ScrapydWeb`_ to manage your Scrapyd cluster.

.. _distutils: http://docs.python.org/library/distutils.html
.. _Twisted Application Framework: http://twistedmatrix.com/documents/current/core/howto/application.html
.. _server command: http://doc.scrapy.org/en/latest/topics/commands.html#server
.. _ScrapydWeb: https://github.com/my8100/scrapydweb
