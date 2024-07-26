========
Overview
========

Projects and versions
=====================

Scrapyd can manage multiple Scrapy projects. Each project can have multiple versions. The latest version is used by default for starting spiders.

.. _overview-order:

Version order
-------------

The latest version is the alphabetically greatest, unless all version names are `version specifiers <https://packaging.python.org/en/latest/specifications/version-specifiers/>`__ like ``1.0`` or ``1.0rc1``, in which case they are sorted as such.

How Scrapyd works
=================

Scrapyd is a server (typically run as a daemon) that listens for :doc:`api` and :ref:`webui` requests.

The API is especially used to upload projects and schedule crawls. To start a crawl, Scrapyd spawns a process that essentially runs:

.. code-block:: shell

   scrapy crawl myspider

Scrapyd runs multiple processes in parallel, and manages the number of concurrent processes. See :ref:`config-launcher` for details.

If you are familiar with the `Twisted Application Framework <https://docs.twisted.org/en/stable/core/howto/application.html>`__, you can essentially reconfigure every part of Scrapyd. See :doc:`config` for details.

.. _webui:

Web interface
=============

Scrapyd has a minimal web interface for monitoring running processes and accessing log files and item fees. By default, it is available at at http://localhost:6800/ Other options to manage Scrapyd include:

-  `ScrapydWeb <https://github.com/my8100/scrapydweb>`__
-  `spider-admin-pro <https://github.com/mouday/spider-admin-pro>`__
