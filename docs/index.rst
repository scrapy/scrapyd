=================
Scrapyd |release|
=================

.. include:: ../README.rst

Quickstart
==========

Install Scrapyd
---------------

.. code-block:: shell

   pip install scrapyd

Start Scrapyd
-------------

.. code-block:: shell

   scrapyd

See :doc:`overview` and :doc:`config` for more details.

Upload a project
----------------

This involves building a `Python egg <https://setuptools.pypa.io/en/latest/deprecated/python_eggs.html>`__ and uploading it to Scrapyd via the `addversion.json <https://scrapyd.readthedocs.org/en/latest/api.html#addversion-json>`_ webservice.

Do this easily with the ``scrapyd-deploy`` command from the `scrapyd-client <https://github.com/scrapy/scrapyd-client>`__ package. Once configured:

.. code-block:: shell

   scrapyd-deploy

Schedule a crawl
----------------

.. code-block:: shell-session

   $ curl http://localhost:6800/schedule.json -d project=myproject -d spider=spider2
   {"status": "ok", "jobid": "26d1b1a6d6f111e0be5c001e648c57f8"}

See :doc:`api` for more details.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   overview
   config
   api
   deploy
   contributing/index
   news
