Deployment
==========

.. _systemd:

Running as a Linux service
--------------------------

On Linux distributions that use systemd, you can run Scrapyd as a service, so that it starts at boot and restarts if it stops.

Create a dedicated user, and a directory for Scrapyd to write to. For example:

.. code-block:: shell

   sudo useradd --system --create-home --home-dir /var/lib/scrapyd --shell /usr/sbin/nologin scrapyd

Create :file:`/etc/systemd/system/scrapyd.service`, replacing the path to the ``scrapyd`` command (run ``which scrapyd`` to find it). If you installed Scrapyd in a virtualenv, use the full path to its :file:`bin/scrapyd`, and make sure the ``scrapyd`` user can read it:

.. code-block:: ini

   [Unit]
   Description=Scrapyd
   After=network.target
   StartLimitIntervalSec=300
   StartLimitBurst=5

   [Service]
   User=scrapyd
   Group=scrapyd
   UMask=2002
   WorkingDirectory=/var/lib/scrapyd
   ExecStart=/usr/local/bin/scrapyd --pidfile=
   Restart=on-failure
   RestartSec=30

   [Install]
   WantedBy=multi-user.target

``WorkingDirectory`` is where Scrapyd writes the relative paths in its default configuration, like :ref:`eggs_dir` and :ref:`dbs_dir`. It is also one of the places :doc:`Scrapyd reads its configuration file from<config>`.

``--pidfile=`` disables the PID file, because systemd tracks the process itself.

``Restart=on-failure`` restarts Scrapyd if it exits with an error or is killed by a signal, but not if you stop it with ``systemctl stop``. Scrapyd sometimes fails to start after an unclean shutdown. ``RestartSec=30`` waits 30 seconds between restarts, and ``StartLimitIntervalSec=300`` with ``StartLimitBurst=5`` stops systemd from retrying after 5 failed starts within 300 seconds.

``Group=scrapyd`` and ``UMask=2002`` make the files Scrapyd writes group-writable, so other users in the ``scrapyd`` group can manage them.

To start Scrapyd now and at every boot:

.. code-block:: shell

   sudo systemctl daemon-reload
   sudo systemctl enable --now scrapyd

Because Scrapyd writes its log to standard output, systemd sends it to the journal:

.. code-block:: shell

   journalctl -u scrapyd

To pass environment variables to Scrapyd and your spiders, add ``Environment`` lines to the ``[Service]`` section. For example, to set a proxy, which `Scrapy respects <https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware>`__:

.. code-block:: ini

   Environment="https_proxy=http://proxy.example.com:3128"
   Environment="no_proxy=localhost,127.0.0.1"

To write the log to a file instead, add the :doc:`--logfile option<cli>` to ``ExecStart``, and make sure the ``scrapyd`` user can write to the file's directory.

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
   jobs_dir          = /var/lib/scrapyd/jobs
   dbs_dir           = /var/lib/scrapyd/dbs
   eggs_dir          = /src/eggs
