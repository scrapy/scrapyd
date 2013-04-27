.. _topics-scrapyd-restapi:

REST API reference
==================

.. versionadded:: 0.18

This section describes the available `RESTful <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ API.

This API follows CRUD standard and provides endpoints for `server`_, `projects`_ and `jobs`_.

Responses can be returned in JSON, XML and YAML. JSON is returned
unless stated in the `Accept` request header.
	
All results are JSON (`Accept: application/json`)::

	$ curl -v -X GET http://localhost:6800/api_v1/server/ -H 'Accept: text/json'

For XML result send `Accept: text/xml`, this is the standard in most browsers::

	$ curl -v -X GET http://localhost:6800/api_v1/server/ -H 'Accept: text/xml'

For YAML result, send `Accept: text/yaml` request header::

	$ curl -v -X GET http://localhost:6800/api_v1/server/ -H 'Accept: text/yaml'

Server
------

Provides information about Scrapyd::

	$ curl -v -X GET http://localhost:6800/api_v1/server/

returns::

	{"status": "ok", "server": {"version": "0.18"}}

Projects
--------

To add a new project, equivalent to `scrapy deploy`::

	$ curl -v -X PUT http://localhost:6800/api_v1/projects/ -F project=myproject -F version=r23 -F egg=@myproject.egg

To get a list of all projects, versions and spiders::

	$ curl -v -X GET http://localhost:6800/api_v1/projects/

To get information of a specific project versions and spiders::

	$ curl -v -X GET http://localhost:6800/api_v1/projects/<PROJECT>

*Where `<PROJECT>` is the name of the project to get the information.*

To get information of a project versions::

	$ curl -v -X GET http://localhost:6800/api_v1/projects/<PROJECT>/versions

To get information of a project spiders::

	$ curl -v -X GET http://localhost:6800/api_v1/projects/<PROJECT>/spiders

To delete an existing project and all versions::

	$ curl -v -X DELETE http://localhost:6800/api_v1/projects/<PROJECT>

To delete a specific version of an existing project::

	$ curl -v -X DELETE http://localhost:6800/api_v1/projects/<PROJECT>/<VERSION>

*Where `<PROJECT>` is the name of the project and `<VERSION>` the version to delete.*

Jobs
----

To schedule a new job::

	$ curl -v -X PUT http://localhost:6800/api_v1/jobs/ -F project=myproject -F spider=myspider

To get a list of all jobs::

	$ curl -v -X GET http://localhost:6800/api_v1/jobs/

To cancel a scheduled or running job::

	$ curl -v -X DELETE http://localhost:6800/api_v1/jobs/<JOB>

*Where `<JOB>` is the id of the job to cancel.*
