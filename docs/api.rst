.. _api:

API
===

The following section describes the available resources in Scrapyd JSON API.

addversion.json
---------------

Add a version to a project, creating the project if it doesn't exist.

* Supported Request Methods: ``POST``
* Parameters:

  * ``project`` (string, required) - the project name
  * ``version`` (string, required) - the project version
  * ``egg`` (file, required) - a Python egg containing the project's code

Example request::

    $ curl http://localhost:6800/addversion.json -F project=myproject -F version=r23 -F egg=@myproject.egg

Example response::

    {"status": "ok", "spiders": 3}

.. _scrapyd-schedule:

schedule.json
-------------

Schedule a spider run (also known as a job), returning the job id.

* Supported Request Methods: ``POST``
* Parameters:

  * ``project`` (string, required) - the project name
  * ``spider`` (string, required) - the spider name
  * ``setting`` (string, optional) - a scrapy setting to use when running the spider
  * any other parameter is passed as spider argument

Example request::

    $ curl http://localhost:6800/schedule.json -d project=myproject -d spider=somespider

Example response::

    {"status": "ok", "jobid": "6487ec79947edab326d6db28a2d86511e8247444"}

Example request passing a spider argument (``arg1``) and a setting
(`DOWNLOAD_DELAY`_)::

    $ curl http://localhost:6800/schedule.json -d project=myproject -d spider=somespider -d setting=DOWNLOAD_DELAY=2 -d arg1=val1

.. _cancel.json:

cancel.json
-----------

.. versionadded:: 0.15

Cancel a spider run (aka. job). If the job is pending, it will be removed. If
the job is running, it will be terminated.

* Supported Request Methods: ``POST``
* Parameters:

  * ``project`` (string, required) - the project name
  * ``job`` (string, required) - the job id

Example request::

    $ curl http://localhost:6800/cancel.json -d project=myproject -d job=6487ec79947edab326d6db28a2d86511e8247444

Example response::

    {"status": "ok", "prevstate": "running"}

listprojects.json
-----------------

Get the list of projects uploaded to this Scrapy server.

* Supported Request Methods: ``GET``
* Parameters: none

Example request::

    $ curl http://localhost:6800/listprojects.json

Example response::

    {"status": "ok", "projects": ["myproject", "otherproject"]}

listversions.json
-----------------

Get the list of versions available for some project. The versions are returned
in order, the last one is the currently used version.

* Supported Request Methods: ``GET``
* Parameters:

  * ``project`` (string, required) - the project name

Example request::

    $ curl http://localhost:6800/listversions.json?project=myproject

Example response::

    {"status": "ok", "versions": ["r99", "r156"]}

listspiders.json
----------------

Get the list of spiders available in the last version of some project.

* Supported Request Methods: ``GET``
* Parameters:

  * ``project`` (string, required) - the project name

Example request::

    $ curl http://localhost:6800/listspiders.json?project=myproject

Example response::

    {"status": "ok", "spiders": ["spider1", "spider2", "spider3"]}

.. _listjobs.json:

listjobs.json
-------------

.. versionadded:: 0.15

Get the list of pending, running and finished jobs of some project.

* Supported Request Methods: ``GET``
* Parameters:

  * ``project`` (string, required) - the project name

Example request::

    $ curl http://localhost:6800/listjobs.json?project=myproject

Example response::

    {"status": "ok",
     "pending": [{"id": "78391cc0fcaf11e1b0090800272a6d06", "spider": "spider1"}],
     "running": [{"id": "422e608f9f28cef127b3d5ef93fe9399", "spider": "spider2", "start_time": "2012-09-12 10:14:03.594664"}],
     "finished": [{"id": "2f16646cfcaf11e1b0090800272a6d06", "spider": "spider3", "start_time": "2012-09-12 10:14:03.594664", "end_time": "2012-09-12 10:24:03.594664"}]}

.. note:: All job data is kept in memory and will be reset when the Scrapyd service is restarted. See `issue 12`_.

delversion.json
---------------

Delete a project version. If there are no more versions available for a given
project, that project will be deleted too.

* Supported Request Methods: ``POST``
* Parameters:

  * ``project`` (string, required) - the project name
  * ``version`` (string, required) - the project version

Example request::

    $ curl http://localhost:6800/delversion.json -d project=myproject -d version=r99

Example response::

    {"status": "ok"}

delproject.json
---------------

Delete a project and all its uploaded versions.

* Supported Request Methods: ``POST``
* Parameters:

  * ``project`` (string, required) - the project name

Example request::

    $ curl http://localhost:6800/delproject.json -d project=myproject

Example response::

    {"status": "ok"}

.. _DOWNLOAD_DELAY: http://doc.scrapy.org/en/latest/topics/settings.html#download-delay
.. _issue 12: https://github.com/scrapy/scrapyd/issues/12
