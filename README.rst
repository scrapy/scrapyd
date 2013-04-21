=======
Scrapyd
=======

.. image:: https://secure.travis-ci.org/scrapy/scrapyd.png?branch=master
   :target: http://travis-ci.org/scrapy/scrapyd

Overview
========

Scrapyd is a service daemon to run (Scrapy)[http://scrapy.org] spiders.

It allows you to deploy your Scrapy projects by building Python eggs of them
and uploading them to the Scrapy service using a (RESTful)[http://en.wikipedia.org/wiki/Representational_state_transfer#RESTful_web_services] and JSON API that you can also use
for scheduling spider runs. It supports multiple projects also.

Frontend
========

Allows to serve a frontend


Requirements
============

* https://github.com/scrapy/scrapy.git master branch or Scrapyd 0.18 or greater
* Python 2.6 or up
* Works on Linux, Windows, Mac OSX, BSD

Install
=======

  Scrapyd is:

  ```
  virtualenv .
  source bin/activate
  pip install -e git+https://github.com/scrapy/scrapyd.git#egg=scrapyd
  scrapyd
  ```

Homepage
========

# Future homepage URL: http://pypi.python.org/pypi/Scrapyd

TODO 
====
* Sphinx Documentation
* Add documentation to ReadTheDocs
* Add project to (Python Package Index)[http://pypi.python.org/pypi/].
* scrapyd command line switches (pid, log, --server-root)
* internal authentication using API_KEY
* launcher
  * os processes
  * async processes (celery)
    * scrapyd-celery - implements launcher
  * rundeck
  * ssh - paramiko
    * screen
  * scrapyd (other with remote access)
  
* Scheduler
  * scrapyd-redis
  * scrapyd-mongo
  * scrapyd-...
  
* events (pydispatch)
  * webhooks - on a schedule finish, etc...
  
* merge former webservices code into REST code


Community (blog, twitter, mail list, IRC)
=========================================

See http://scrapy.org/community/

Contributing
============

See http://doc.scrapy.org/en/latest/contributing.html

Companies using Scrapy
======================

See http://scrapy.org/companies/

Commercial Support
==================

See http://scrapy.org/support/
