Deployment
==========

Deploying a Scrapy project
--------------------------

This involves building a `Python egg <https://setuptools.pypa.io/en/latest/deprecated/python_eggs.html>`__ and uploading it to Scrapyd via the `addversion.json <https://scrapyd.readthedocs.org/en/latest/api.html#addversion-json>`_ webservice. Do this easily with the `scrapyd-deploy` command from the `scrapyd-client <https://github.com/scrapy/scrapyd-client>`__ package.

.. _docker:

Creating a Docker image
-----------------------

If you prefer to create a Docker image for the Scrapyd service and your Scrapy projects, you can copy this ``Dockerfile`` template into your Scrapy project, and adapt it.

.. code-block:: dockerfile

   # Build an egg of your project.

   FROM python as build-stage

   RUN pip install --no-cache-dir scrapyd-client

   WORKDIR /workdir

   COPY . .

   RUN scrapyd-deploy --build-egg=myproject.egg

   # Build the image.

   FROM python:alpine

   # Install Scrapy dependencies - and any others for your project.

   RUN apk --no-cache add --virtual build-dependencies \
      gcc \
      musl-dev \
      libffi-dev \
      libressl-dev \
      libxml2-dev \
      libxslt-dev \
    && pip install --no-cache-dir \
      scrapyd \
    && apk del build-dependencies \
    && apk add \
      libressl \
      libxml2 \
      libxslt

   # Mount two volumes for configuration and runtime.

   VOLUME /etc/scrapyd/ /var/lib/scrapyd/

   COPY ./scrapyd.conf /etc/scrapyd/

   RUN mkdir -p /src/eggs/myproject

   COPY --from=build-stage /workdir/myproject.egg /src/eggs/myproject/1.egg

   EXPOSE 6800

   ENTRYPOINT ["scrapyd", "--pidfile="]

Where your ``scrapy.cfg`` file, used by ``scrapyd-deploy``, might be:

.. code-block:: ini

   [settings]
   default = myproject.settings

   [deploy]
   url = http://localhost:6800
   project = myproject

And your ``scrapyd.conf`` file might be:

.. code-block:: ini

   [scrapyd]
   bind_address      = 0.0.0.0
   logs_dir          = /var/lib/scrapyd/logs
   items_dir         = /var/lib/scrapyd/items
   dbs_dir           = /var/lib/scrapyd/dbs
   eggs_dir          = /src/eggs
