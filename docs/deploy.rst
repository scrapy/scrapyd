.. _deploy:

Deploying your project
======================

Deploying your project into a Scrapyd server typically involves two steps:

1. building a `Python egg`_ of your project. This is called "eggifying" your
   project. You'll need to install `setuptools`_ for this. See
   :ref:`topics-egg-caveats` below.

2. uploading the egg to the Scrapyd server

The simplest way to deploy your project is by using the `deploy command`_,
which automates the process of building the egg uploading it using the Scrapyd
HTTP JSON API.

The `deploy command`_ supports multiple targets (Scrapyd servers that can host
your project) and each target supports multiple projects.

Each time you deploy a new version of a project, you can name it for later
reference.

Show and define targets
-----------------------

To see all available targets type::

    scrapyd-deploy -l

This will return a list of available targets and their URLs. For example::

    scrapyd              http://localhost:6800/

You can define targets by adding them to your project's ``scrapy.cfg`` file,
or any other supported location like ``~/.scrapy.cfg``, ``/etc/scrapy.cfg``,
or ``c:\scrapy\scrapy.cfg`` (in Windows).

Here's an example of defining a new target ``scrapyd2`` with restricted access
through HTTP basic authentication::

    [deploy:scrapyd2]
    url = http://scrapyd.mydomain.com/api/scrapyd/
    username = john
    password = secret

.. note:: The `deploy command`_ also supports netrc for getting the credentials.

Now, if you type ``scrapyd-deploy -l`` you'll see::

    scrapyd              http://localhost:6800/
    scrapyd2             http://scrapyd.mydomain.com/api/scrapyd/

See available projects
----------------------

To see all available projects in a specific target use::

    scrapyd-deploy -L scrapyd

It would return something like this::

    project1
    project2

Deploying a project
-------------------

Finally, to deploy your project use::

    scrapyd-deploy scrapyd -p project1

This will eggify your project and upload it to the target, printing the JSON
response returned from the Scrapyd server. If you have a ``setup.py`` file in
your project, that one will be used. Otherwise a ``setup.py`` file will be
created automatically (based on a simple template) that you can edit later.

After running that command you will see something like this, meaning your
project was uploaded successfully::

    Deploying myproject-1287453519 to http://localhost:6800/addversion.json
    Server response (200):
    {"status": "ok", "spiders": ["spider1", "spider2"]}

By default ``scrapyd-deploy`` uses the current timestamp for generating the
project version, as you can see in the output above. However, you can pass a
custom version with the ``--version`` option::

    scrapyd-deploy scrapyd -p project1 --version 54

Also, if you use Mercurial for tracking your project source code, you can use
``HG`` for the version which will be replaced by the current Mercurial
revision, for example ``r382``::

    scrapyd-deploy scrapyd -p project1 --version HG

And, if you use Git for tracking your project source code, you can use
``GIT`` for the version which will be replaced by the SHA1 of current Git
revision, for example ``b0582849179d1de7bd86eaa7201ea3cda4b5651f``::

    scrapyd-deploy scrapyd -p project1 --version GIT

Support for other version discovery sources may be added in the future.

Finally, if you don't want to specify the target, project and version every
time you run ``scrapyd-deploy`` you can define the defaults in the
``scrapy.cfg`` file. For example::

    [deploy]
    url = http://scrapyd.mydomain.com/api/scrapyd/
    username = john
    password = secret
    project = project1
    version = HG

This way, you can deploy your project just by using::

    scrapyd-deploy

Local settings
--------------

Sometimes, while your working on your projects, you may want to override your
certain settings with certain local settings that shouldn't be deployed to
Scrapyd, but only used locally to develop and debug your spiders.

One way to deal with this is to have a ``local_settings.py`` at the root of
your project (where the ``scrapy.cfg`` file resides) and add these lines to the
end of your project settings::

    try:
        from local_settings import *
    except ImportError:
        pass

``scrapyd-deploy`` won't deploy anything outside the project module so the
``local_settings.py`` file won't be deployed.

Here's the directory structure, to illustrate::

    scrapy.cfg
    local_settings.py
    myproject/
        __init__.py
        settings.py
        spiders/
            ...

.. _topics-egg-caveats:

Egg caveats
-----------

There are some things to keep in mind when building eggs of your Scrapy
project:

* make sure no local development settings are included in the egg when you
  build it. The ``find_packages`` function may be picking up your custom
  settings. In most cases you want to upload the egg with the default project
  settings.

* you shouldn't use ``__file__`` in your project code as it doesn't play well
  with eggs. Consider using `pkgutil.get_data()`_ instead.

* be careful when writing to disk in your project (in any spider, extension or
  middleware) as Scrapyd will probably run with a different user which may not
  have write access to certain directories. If you can, avoid writing to disk
  and always use `tempfile`_ for temporary files.

.. _Python egg: http://peak.telecommunity.com/DevCenter/PythonEggs
.. _deploy command: http://doc.scrapy.org/en/latest/topics/commands.html#deploy
.. _setuptools: http://pypi.python.org/pypi/setuptools
.. _pkgutil.get_data(): http://docs.python.org/library/pkgutil.html#pkgutil.get_data
.. _tempfile: http://docs.python.org/library/tempfile.html
