.. Scrapyd documentation master file, created by
   sphinx-quickstart on Sat Apr 20 08:49:39 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Scrapyd
=======

Scrapyd is a service (typically run as a daemon)Scrapyd for Scrapy that allows you to deploy (aka. upload) your projects and control their spiders using web services.

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
number of slots given by the `max_proc`_ and `max_proc_per_cpu`_ options,
starting as many processes as possible to handle the load.

In addition to dispatching and managing processes, Scrapyd provides a
:ref:`JSON web service <topics-scrapyd-jsonapi>` to upload new project versions
(as eggs) and schedule spiders. This feature is optional and can be disabled if
you want to implement your own custom Scrapyd. The components are pluggable and
can be changed, if you're familiar with the `Twisted Application Framework`_
which Scrapyd is implemented in.

Starting from 0.11, Scrapyd also provides a minimal :ref:`web interface
<topics-scrapyd-webui>`.

Contents:

.. toctree::
   :maxdepth: 2

   scrapyd
   installing
   common
   jsonapi


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

