.. _install:

Installation
============

This documents explains how to install and configure Scrapyd, to deploy and run
your Scrapy spiders.

Requirements
------------

Scrapyd depends on the following libraries, but the installation process
takes care of installing the missing ones:

* Python 2.6 or above
* Twisted 8.0 or above
* Scrapy 0.17 or above

Installing Scrapyd (generic way)
--------------------------------

How to install Scrapyd depends on the platform you're using. The generic way is
to install it from PyPI::

    pip install scrapyd

If you plan to deploy Scrapyd in Ubuntu, Scrapyd comes with official Ubuntu
packages (see below) for installing it as a system service, which eases the
administration work.

Other distributions and operating systems (Windows, Mac OS X) don't yet have
specific packages and require to use the generic installation mechanism in
addition to configuring paths and enabling it run as a system service. You are
very welcome to contribute Scrapyd packages for your platform of choice, just
send a pull request on Github.


Installing Scrapyd in Ubuntu
----------------------------

Scrapyd comes with official Ubuntu packages ready to use in your Ubuntu
servers. They are shipped in the same APT repos of Scrapy, which can be added
as described in `Scrapy Ubuntu packages`_. Once you have added the Scrapy APT
repos, you can install Scrapyd with ``apt-get``::

    apt-get install scrapyd

This will install Scrapyd in your Ubuntu server creating a ``scrapy`` user
which Scrapyd will run as. It will also create the directories and files
described below:

/etc/scrapyd
~~~~~~~~~~~~

Scrapyd configuration files. See :ref:`config`.

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

.. _Scrapy Ubuntu packages: http://doc.scrapy.org/en/latest/topics/ubuntu.html
