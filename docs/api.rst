.. _api:

API
===

The following section describes the available resources in Scrapyd JSON API.

If basic authentication is enabled, you can use ``curl`` with the ``-u`` option, for example:

.. code-block:: shell

    curl -u yourusername:yourpassword http://localhost:6800/daemonstatus.json

.. _daemonstatus.json:

daemonstatus.json
-----------------

To check the load status of a service.

Supported request methods
  ``GET``

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/daemonstatus.json
   {"node_name": "mynodename", "status": "ok", "pending": 0, "running": 0, "finished": 0}

.. _addversion.json:

addversion.json
---------------

Add a version to a project, creating the project if needed.

Supported request methods
  ``POST``
Parameters
  ``project`` (required)
    the project name
  ``version`` (required)
    the project version
  ``egg`` (required)
    a Python egg containing the project's code

.. note:: Scrapyd uses the `packaging Version <https://packaging.pypa.io/en/stable/version.html>`__ to interpret the version numbers you provide.

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/addversion.json -F project=myproject -F version=r23 -F egg=@myproject.egg
   {"node_name": "mynodename", "status": "ok", "spiders": 3}

.. _schedule.json:

schedule.json
-------------

Schedule a job. (A job is a `Scrapy crawl <https://docs.scrapy.org/en/latest/topics/commands.html#crawl>`__.)

Supported request methods
  ``POST``
Parameters
  ``project`` (required)
    the project name
  ``spider`` (required)
    the spider name
  ``_version``
    the project version (the latest project version by default)
  ``jobid``
    the job's ID (a hexadecimal UUID v1 by default)
  ``priority``
    the job's priority in the project's spider queue (0 by default, higher number, higher priority)
  ``setting``
    a Scrapy setting

    For example, using `DOWNLOAD_DELAY <http://doc.scrapy.org/en/latest/topics/settings.html#download-delay>`__:

    .. code-block:: shell

        curl http://localhost:6800/schedule.json -d setting=DOWNLOAD_DELAY=2 -d project=myproject -d spider=somespider
  Any other parameter
    a spider argument

    For example, using ``arg1``:

    .. code-block:: shell

       curl http://localhost:6800/schedule.json -d arg1=val1 -d project=myproject -d spider=somespider

If the :ref:`logs_dir` setting is set, log files are written to ``{logs_dir}/{project}/{spider}/{jobid}.log``.
Set the ``jobid`` parameter to configure the basename of the log file.

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/schedule.json -d project=myproject -d spider=somespider
   {"node_name": "mynodename", "status": "ok", "jobid": "6487ec79947edab326d6db28a2d86511e8247444"}

.. note::

    Spiders scheduled with Scrapyd should allow for an arbitrary number of keyword arguments,
    as Scrapyd sends internally-generated spider arguments to the spider being scheduled.

.. note::

    When a parameter other than ``setting`` is entered multiple times with ``-d``, only the first
    value is sent to the spider.

.. _status.json:

status.json
-----------

.. versionadded:: 1.5.0

Get the status of a job.

Supported request methods
  ``GET``
Parameters
  ``job`` (required)
    the job ID
  ``project``
    the project name

Example:

.. code-block:: shell-session

    $ curl http://localhost:6800/status.json?job=6487ec79947edab326d6db28a2d86511e8247444
    {"node_name": "mynodename", "status": "ok", "currstate": "running"}

.. _cancel.json:

cancel.json
-----------

Cancel a job.

-  If the job is pending, it is removed from the project's spider queue.
-  If the job is running, the process is sent a signal to terminate.

Supported request methods
  ``POST``
Parameters
  ``project`` (required)
    the project name
  ``job`` (required)
    the job ID

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/cancel.json -d project=myproject -d job=6487ec79947edab326d6db28a2d86511e8247444
   {"node_name": "mynodename", "status": "ok", "prevstate": "running"}

.. _listprojects.json:

listprojects.json
-----------------

Get the projects.

Supported request methods
  ``GET``

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/listprojects.json
   {"node_name": "mynodename", "status": "ok", "projects": ["myproject", "otherproject"]}

.. _listversions.json:

listversions.json
-----------------

Get the versions of a project, in order, with the latest version last.

Supported request methods
  ``GET``
Parameters
  ``project`` (required)
    the project name

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/listversions.json?project=myproject
   {"node_name": "mynodename", "status": "ok", "versions": ["r99", "r156"]}

.. _listspiders.json:

listspiders.json
----------------

Get the spiders in a version of a project.

Supported request methods
  ``GET``
Parameters
  ``project`` (required)
    the project name
  ``_version``
    the project version (the latest project version by default)

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/listspiders.json?project=myproject
   {"node_name": "mynodename", "status": "ok", "spiders": ["spider1", "spider2", "spider3"]}

.. _listjobs.json:

listjobs.json
-------------

Get the pending, running and finished jobs of a project.

-  Pending jobs are in :ref:`spider queues<spiderqueue>`.
-  Running jobs have Scrapy processes.
-  Finished jobs are in job storage.

   .. note:: The default :ref:`jobstorage` setting stores jobs in memory, such that jobs are lost when the Scrapyd process ends.

Supported request methods
  ``GET``
Parameters
  ``project``
    filter results by project name

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/listjobs.json?project=myproject | python -m json.tool
   {
       "node_name": "mynodename",
       "status": "ok",
       "pending": [
           {
               "project": "myproject", "spider": "spider1",
               "id": "78391cc0fcaf11e1b0090800272a6d06"
           }
       ],
       "running": [
           {
               "id": "422e608f9f28cef127b3d5ef93fe9399",
               "project": "myproject", "spider": "spider2",
               "start_time": "2012-09-12 10:14:03.594664"
           }
       ],
       "finished": [
           {
               "id": "2f16646cfcaf11e1b0090800272a6d06",
               "project": "myproject", "spider": "spider3",
               "start_time": "2012-09-12 10:14:03.594664",
               "end_time": "2012-09-12 10:24:03.594664",
               "log_url": "/logs/myproject/spider3/2f16646cfcaf11e1b0090800272a6d06.log",
               "items_url": "/items/myproject/spider3/2f16646cfcaf11e1b0090800272a6d06.jl"
           }
       ]
   }

.. _delversion.json:

delversion.json
---------------

Delete a version of a project. If no versions of the project remain, delete the project, too.

Supported request methods
  ``POST``
Parameters
  ``project`` (required)
    the project name
  ``version`` (required)
    the project version

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/delversion.json -d project=myproject -d version=r99
   {"node_name": "mynodename", "status": "ok"}

.. _delproject.json:

delproject.json
---------------

Delete a project and its versions.

Supported request methods
  ``POST``
Parameters
  ``project`` (required)
      the project name

Example:

.. code-block:: shell-session

   $ curl http://localhost:6800/delproject.json -d project=myproject
   {"node_name": "mynodename", "status": "ok"}
