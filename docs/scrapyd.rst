.. _topics-scrapyd:

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

Scrapyd continually polls for spiders that need to run.

When a spider needs to run, a process is started to crawl the spider::

    scrapy crawl myspider

Scrapyd also runs multiple processes in parallel, allocating them in a fixed
number of slots given by the :ref:`max_proc` and :ref:`max_proc_per_cpu` options,
starting as many processes as possible to handle the load.

In addition to dispatching and managing processes, Scrapyd provides a
:ref:`JSON web service <topics-scrapyd-jsonapi>` to upload new project versions
(as eggs) and schedule spiders. This feature is optional and can be disabled if
you want to implement your own custom Scrapyd. The components are pluggable and
can be changed, if you're familiar with the `Twisted Application Framework`_
which Scrapyd is implemented in.

Starting from 0.11, Scrapyd also provides a minimal :ref:`web interface
<topics-scrapyd-webui>`.

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

.. _topics-scrapyd-webui:

Web Interface
=============

Scrapyd comes with a web interface (for monitoring running processes
and accessing logs) which can be accessed at http://localhost:6800/

Create a custom web interface
-----------------------------

.. versionadded:: 0.18

To create your own web interface use :ref:`htdocs_dir` setting to specify the 
folder containing a `index.html` filename.

.. _distutils: http://docs.python.org/library/distutils.html
.. _Twisted Application Framework: http://twistedmatrix.com/documents/current/core/howto/application.html
