Installation
============

How to deploy Scrapyd on your servers depends on the platform you're using.
Scrapy comes with Ubuntu packages for Scrapyd ready for deploying it as a
system service, to ease the installation and administration, but you can create
packages for other distribution or operating systems (including Windows). If
you do so, and want to contribute them, send a message to
scrapy-developers@googlegroups.com and say hi. The community will appreciate
it.

.. _topics-scrapyd-ubuntu:

Installing Scrapyd in Ubuntu
----------------------------

When deploying Scrapyd, it's very useful to have a version already packaged for
your system. For this reason, Scrapyd comes with Ubuntu packages ready to use
in your Ubuntu servers.

So, if you plan to deploy Scrapyd on a Ubuntu server, just add the Ubuntu
repositories as described in scrapy documentation and then run::

    aptitude install scrapyd-X.YY

Where ``X.YY`` is the Scrapy version, for example: ``0.14``.

This will install Scrapyd in your Ubuntu server creating a ``scrapy`` user
which Scrapyd will run as. It will also create some directories and files that
are listed below:

/etc/scrapyd
~~~~~~~~~~~~

Scrapyd configuration files. See :ref:`topics-scrapyd-config`.

/var/log/scrapyd/scrapyd.log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scrapyd main log file.

/var/log/scrapyd/scrapyd.out
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standard output captured from Scrapyd process and any
sub-process spawned from it.

/var/log/scrapyd/scrapyd.err
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standard error captured from Scrapyd and any sub-process spawned
from it. Remember to check this file if you're having problems, as the errors
may not get logged to the ``scrapyd.log`` file.

/var/log/scrapyd/project
~~~~~~~~~~~~~~~~~~~~~~~~

Besides the main service log file, Scrapyd stores one log file per crawling
process in::

    /var/log/scrapyd/PROJECT/SPIDER/ID.log

Where ``ID`` is a unique id for the run.

/var/lib/scrapyd/
~~~~~~~~~~~~~~~~~

Directory used to store data files (uploaded eggs and spider queues).

