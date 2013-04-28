.. _topics-scrapyd-restapi:

##################
REST API reference
##################

.. versionadded:: 0.18

This section describes the available `RESTful <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ API.

This API follows CRUD standard and provides endpoints for `server`_, `projects`_ and `jobs`_.

Responses can be returned in JSON, XML and YAML. JSON is returned
unless stated in the `Accept` request header.
	
All returned results are JSON::

	$ curl http://localhost:6800/api_v1/server/

Example response::
	
	{"status": "ok", "server": {"version": "0.17.1"}}	

To implicitly specify JSON as result format, send ``Accept: application/json`` in your request headers, like in ``curl http://localhost:6800/api_v1/server/ -H 'Accept: text/json'``.

For XML result send ``Accept: text/xml``, this is the standard in most browsers::

	$ curl http://localhost:6800/api_v1/server/ -H 'Accept: text/xml'

Example response::

	<item><status>ok</status><server><version>0.17.1</version></server></item>

For YAML result, send ``Accept: text/yaml`` request header::

	$ curl http://localhost:6800/api_v1/server/ -H 'Accept: text/yaml'

Example response::

	server: {version: 0.17.1}
	status: ok

.. warning:: A web browser will possibly return XML format because the presence of xml in ``Accept`` header.

.. _server:

Status of the server
--------------------

To obtain information about the server, send a ``GET`` request to ``/api_v1/server/``::

	$ curl http://localhost:6800/api_v1/server/

and the returning information will be similar to::

	{"status": "ok", "server": {"version": "0.18"}}

.. _projects:

Add a new project
-----------------

To add a new project, equivalent to ``scrapy deploy``, send a ``PUT`` request to 
``/api_v1/projects/`` with the parameters:

* ``project`` - the project name
* ``version`` - the project version
* ``egg`` - a file containing a Python egg with the project's code.

Example::

	$ curl -X PUT http://localhost:6800/api_v1/projects/ -F project=myproject -F version=r23 -F egg=@myproject.egg

List existing projects
----------------------

To retrieve a list of all projects, versions and spiders, send a ``GET`` request to ``/api_v1/projects/``::

	$ curl http://localhost:6800/api_v1/projects/

Get project versions and spiders
--------------------------------

To obtain information of a specific project versions and spiders, 
send a ``GET`` request to ``/api_v1/projects/<PROJECT>``, where ``<PROJECT>`` 
is the name of the project to get the information.

The following example will retrieve information on ``my_project``::

	$ curl http://localhost:6800/api_v1/projects/my_project


Delete a project
----------------

To delete an existing project and all versions, send a ``DELETE`` request
to ``/api_v1/projects/<PROJECT>``, where ``<PROJECT>`` 
is the name of the project to delete::

	$ curl -X DELETE http://localhost:6800/api_v1/projects/my_project


Delete a version of a project
-----------------------------

To delete a specific version of an existing project, send a ``DELETE`` request
to ``/api_v1/projects/<PROJECT>/<VERSION>``, where ``<PROJECT>`` is the name 
of the project and ``<VERSION>`` the version to delete::

	$ curl -X DELETE http://localhost:6800/api_v1/projects/my_project/my_version

.. _jobs:

Schedule a job
--------------

To schedule a new job, send a ``PUT`` request to ``/api_v1/jobs/`` with 
the following parameters:

  * ``project`` (string, required) - the project name
  * ``spider`` (string, required) - the spider name
  * ``setting`` (string, optional) - a scrapy setting to use when running the spider
  * any other parameter is passed as spider argument

Schedule xample::

	$ curl -X PUT http://localhost:6800/api_v1/jobs/ -F project=myproject -F spider=myspider

List jobs
---------

To get a list of all jobs, send a ``GET`` request to ``/api_v1/jobs/``::

	$ curl http://localhost:6800/api_v1/jobs/

Cancel a job
------------

To cancel a scheduled or running job, send a ``DELETE`` request 
to ``/api_v1/jobs/<JOB>`` where ``<JOB>`` is the Job ID.

Cancel example::

	$ curl -X DELETE http://localhost:6800/api_v1/jobs/<JOB>


Extending REST Api
------------------

It is possible to create new REST functionalities to Scrapyd by adding 
a valid resource to ``api_v1`` section in ``scrapyd.conf``, for more 
information read the :ref:`topics-scrapyd-config-example`.


