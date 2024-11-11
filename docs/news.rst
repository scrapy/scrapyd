Release notes
=============

.. changelog

Unreleased
----------

Removed
~~~~~~~

- Drop support for end-of-life Python version 3.8.

1.5.0 (2024-09-05)
------------------

Added
~~~~~

- Default webservices can be disabled. See :ref:`config-services`.

Fixed
~~~~~

- Restore the ``--nodaemon`` (``-n``) option (which Scrapyd enables, regardless), to avoid "option --nodaemon not recognized".

1.5.0b1 (2024-07-25)
--------------------

This release contains the most changes in a decade. Therefore, a beta release is made first.

Added
~~~~~

- Add ``version`` (egg version), ``settings`` (Scrapy settings) and ``args`` (spider arguments) to the pending jobs in the response from the :ref:`listjobs.json` webservice.
- Add ``log_url`` and ``items_url`` to the running jobs in the response from the :ref:`listjobs.json` webservice.
- Add a :ref:`status.json` webservice, to get the status of a job.
- Add a :ref:`unix_socket_path` setting, to listen on a Unix socket.
- Add a :ref:`poller` setting.
- Respond to HTTP ``OPTIONS`` method requests.
- Add environment variables to override common options. See :ref:`config-envvars`.

Documentation
^^^^^^^^^^^^^

- How to add webservices (endpoints). See :ref:`config-services`.
- How to create Docker images. See :ref:`docker`.
- How to integrate Scrapy projects, without eggs. See :ref:`config-settings`.

Changed
~~~~~~~

- Every :ref:`poll_interval`, up to :ref:`max_proc` processes are started by the default :ref:`poller`, instead of only one process. (The number of running jobs will not exceed :ref:`max_proc`.)

Web UI
^^^^^^

- Add basic CSS.
- Add a confirmation dialog to the Cancel button.
- Add "Last modified" column to the directory listings of log files and item feeds.
- The Jobs page responds only to HTTP ``GET`` and ``HEAD`` method requests.

API
^^^

- Clarify error messages, for example:

  - ``'project' parameter is required``, instead of ``'project'`` (KeyError)
  - ``project 'myproject' not found``, instead of ``'myproject'`` (KeyError)
  - ``project 'myproject' not found``, instead of ``Scrapy VERSION - no active project``
  - ``version 'myversion' not found``, instead of a traceback
  - ``exception class: message``, instead of ``message``
  - ``BadEggError``, instead of ``TypeError: 'tuple' object is not an iterator``
  - Error messages for non-UTF-8 bytes and non-float ``priority``.
  - "Unsupported method" error messages no longer list ``object`` as an allowed HTTP method

CLI
^^^

- Scrapyd uses ``twisted.logger`` instead of the legacy ``twisted.python.log``. Some system information changes:

  - ``[scrapyd.basicauth#info] Basic authentication ...``, instead of ``[-] ...``
  - ``[scrapyd.app#info] Scrapyd web console available at ...``, instead of ``[-] ...``
  - ``[-] Unhandled Error``, instead of ``[_GenericHTTPChannelProtocol,0,127.0.0.1] ...``
  - Data received from standard error and non-zero exit status codes are logged at error level.

- Correct the usage message and long description.
- Remove the ``--rundir`` option, which only works if ``*_dir`` settings are absolute paths.
- Remove the ``--nodaemon`` (``-n``) option, which Scrapyd enables.
- Remove the ``--python=`` (``-y``) option, which Scrapyd needs to set to its application.
- Remove all ``twistd`` subcommands (FTP servers, etc.). Run ``twistd``, if needed.
- Run the ``scrapyd.__main__`` module, instead of the ``scrapyd.scripts.scrapyd_run`` module.

Library
^^^^^^^

- Move functions from ``scrapyd.utils`` into their callers:

  - ``sorted_versions`` to ``scrapyd.eggstorage``
  - ``get_crawl_args`` to ``scrapyd.launcher``

- :ref:`jobstorage` uses the ``ScrapyProcessProtocol`` class, by default. If :ref:`jobstorage` is set to ``scrapyd.jobstorage.SqliteJobStorage``, Scrapyd 1.3.0 uses a ``Job`` class, instead. To promote parity, the ``Job`` class is removed.
- Move the ``activate_egg`` function from the ``scrapyd.eggutils`` module to its caller, the ``scrapyd.runner`` module.
- Move the ``job_log_url`` and ``job_items_url`` functions into the ``Root`` class, since the ``Root`` class is responsible for file URLs.
- Change the ``get_crawl_args`` function to no longer convert ``bytes`` to ``str``, as already done by its caller.
- Change the ``scrapyd.app.create_wrapped_resource`` function to a ``scrapyd.basicauth.wrap_resource`` function.
- Change the ``scrapyd.utils.sqlite_connection_string`` function to an ``scrapyd.sqlite.initialize`` function.
- Change the ``get_spider_list`` function to a ``SpiderList`` class.
- Merge the ``JsonResource`` class into the ``WsResource`` class, removing the ``render_object`` method.

Fixed
~~~~~

- Restore support for :ref:`eggstorage` implementations whose ``get()`` methods return file-like objects without ``name`` attributes (1.4.3 regression).
- If the :ref:`items_dir` setting is a URL and the path component ends with ``/``, the ``FEEDS`` setting no longer contains double slashes.
- The ``MemoryJobStorage`` class returns finished jobs in reverse chronological order, like the ``SqliteJobStorage`` class.
- The ``list_projects`` method of the ``SpiderScheduler`` class returns a ``list``, instead of ``dict_keys``.
- Log errors to Scrapyd's log, even when :ref:`debug` mode is enabled.
- List the closest ``scrapy.cfg`` file as a :ref:`configuration source<config-sources>`.

API
^^^

- The ``Content-Length`` header counts the number of bytes, instead of the number of characters.
- The ``Access-Control-Allow-Methods`` response header contains only the HTTP methods to which webservices respond.
- The :ref:`listjobs.json` webservice sets the ``log_url`` and ``items_url`` fields to ``null`` if the files don't exist.
- The :ref:`schedule.json` webservice sets the ``node_name`` field in error responses.
- The next pending job for all but one project was unreported by the :ref:`daemonstatus.json` and :ref:`listjobs.json` webservices, and was not cancellable by the :ref:`cancel.json` webservice.

Security
^^^^^^^^

- The ``FilesystemEggStorage`` class used by the :ref:`listversions.json` webservice escapes project names (used in glob patterns) before globbing, to disallow listing arbitrary directories.
- The ``FilesystemEggStorage`` class used by the :ref:`runner` and the :ref:`addversion.json`,  :ref:`listversions.json`, :ref:`delversion.json` and :ref:`delproject.json` webservices raises a ``DirectoryTraversalError`` error if the project parameter (used in file paths) would traverse directories.
- The ``Environment`` class used by the :ref:`launcher` raises a ``DirectoryTraversalError`` error if the project, spider or job parameters (used in file paths) would traverse directories.
- The :ref:`webui` escapes user input (project names, spider names, and job IDs) to prevent cross-site scripting (XSS).

Platform support
^^^^^^^^^^^^^^^^

Scrapyd is now tested on macOS and Windows, in addition to Linux.

- The :ref:`cancel.json` webservice now works on Windows, by using SIGBREAK instead of SIGINT or SIGTERM.
- The :ref:`dbs_dir` setting no longer causes an error if it contains a drive letter on Windows.
- The :ref:`items_dir` setting is considered a local path if it contains a drive letter on Windows.
- The :ref:`jobs_to_keep` setting no longer causes an error if a file to delete can't be deleted (for example, if the file is open on Windows).

Removed
~~~~~~~

- Remove support for parsing URLs in :ref:`dbs_dir`, since SQLite writes only to paths or ``:memory:`` (added in 1.4.2).
- Remove the ``JsonSqliteDict`` and ``UtilsCache`` classes.
- Remove the ``native_stringify_dict`` function.
- Remove undocumented and unused internal environment variables:

  - ``SCRAPYD_FEED_URI``
  - ``SCRAPYD_JOB``
  - ``SCRAPYD_LOG_FILE``
  - ``SCRAPYD_SLOT``
  - ``SCRAPYD_SPIDER``

- Drop support for end-of-life Python version 3.7.

1.4.3 (2023-09-25)
------------------

Changed
~~~~~~~

- Change project from comma-separated list to bulleted list on landing page. (@bsekiewicz)

Fixed
~~~~~

- Fix "The process cannot access the file because it is being used by another process" on Windows.

1.4.2 (2023-05-01)
------------------

Added
~~~~~

- Add a :ref:`spiderqueue` setting. Since this was not previously configurable, the changes below are considered backwards-compatible.
- Add support for the X-Forwarded-Prefix HTTP header. Rename this header using the :ref:`prefix_header` setting.

Changed
~~~~~~~

- ``scrapyd.spiderqueue.SqliteSpiderQueue`` is initialized with a ``scrapyd.config.Config`` object and a project name, rather than a SQLite connection string (i.e. database file path).
- If :ref:`dbs_dir` is set to ``:memory:`` or to a URL, it is passed through without modification and without creating a directory to ``scrapyd.jobstorage.SqliteJobStorage`` and ``scrapyd.spiderqueue.SqliteSpiderQueue``.
- ``scrapyd.utils.get_spider_queues`` defers the creation of the :ref:`dbs_dir` directory to the spider queue implementation.

1.4.1 (2023-02-10)
------------------

Fixed
~~~~~

- Encode the ``FEEDS`` command-line argument as JSON.

1.4.0 (2023-02-07)
------------------

Added
~~~~~

- Add ``log_url`` and ``items_url`` to the finished jobs in the response from the :ref:`listjobs.json` webservice. (@mxdev88)
- Scrapy 2.8 support. Scrapyd sets ``LOG_FILE`` and ``FEEDS`` command-line arguments, instead of ``SCRAPY_LOG_FILE`` and ``SCRAPY_FEED_URI`` environment variables.
- Python 3.11 support.
- Python 3.12 support. Use ``packaging.version.Version`` instead of ``distutils.LooseVersion``. (@pawelmhm)

Changed
~~~~~~~

- Rename environment variables to avoid spurious Scrapy deprecation warnings.

  - ``SCRAPY_EGG_VERSION`` to ``SCRAPYD_EGG_VERSION``
  - ``SCRAPY_FEED_URI`` to ``SCRAPYD_FEED_URI``
  - ``SCRAPY_JOB`` to ``SCRAPYD_JOB``
  - ``SCRAPY_LOG_FILE`` to ``SCRAPYD_LOG_FILE``
  - ``SCRAPY_SLOT`` to ``SCRAPYD_SLOT``
  - ``SCRAPY_SPIDER`` to ``SCRAPYD_SPIDER``

  .. attention:: Except for ``SCRAPYD_EGG_VERSION``, these are undocumented and unused, and may be removed in future versions. If you use these environment variables, please `report your use in an issue <https://github.com/scrapy/scrapyd/issues>`__.

Removed
~~~~~~~

- Scrapy 1.x support.
- Python 3.6 support.
- Unmaintained files (Debian packaging) and unused code (``scrapyd/script.py``).

Fixed
~~~~~

- Print Scrapyd's version instead of Twisted's version with ``--version`` (``-v``) flag. (@niuguy)
- Override Scrapy's ``LOG_STDOUT`` setting to ``False`` to suppress logging output for :ref:`listspiders.json` webservice. (@Lucioric2000)

1.3.0 (2022-01-12)
------------------

Added
~~~~~

- Add :ref:`username` and :ref:`password` settings, for HTTP authentication.
- Add :ref:`jobstorage` and :ref:`eggstorage` settings.
- Add a ``priority`` argument to the :ref:`schedule.json` webservice.
- Add ``project`` to all jobs in the response from the :ref:`listjobs.json` webservice.
- Add shortcut to jobs page to cancel a job using the :ref:`cancel.json` webservice.
- Python 3.7, 3.8, 3.9, 3.10 support.

Changed
~~~~~~~

- Make optional the ``project`` argument to the :ref:`listjobs.json` webservice, to easily query for all jobs.
- Improve HTTP headers across webservices.

Removed
~~~~~~~

- Python 2, 3.3, 3.4, 3.5 support.
- PyPy 2 support.
- Documentation for Ubuntu installs (Zyte no longer maintains the Ubuntu package).

Fixed
~~~~~

- Respect Scrapy's ``TWISTED_REACTOR`` setting.
- Replace deprecated ``SafeConfigParser`` with ``ConfigParser``.

1.2.1 (2019-06-17)
------------------

Fixed
~~~~~

- Fix HTTP header types for newer Twisted versions.
- ``DeferredQueue`` no longer hides a pending job when reaching :ref:`max_proc`.
- The :ref:`addversion.json` webservice now works on Windows.
- test: Update binary eggs to be compatible with Scrapy 1.x.

Removed
~~~~~~~

- Remove deprecated SQLite utilities.

1.2.0 (2017-04-12)
------------------

Added
~~~~~

- Webservice

  - Add the :ref:`daemonstatus.json` webservice.
  - Add a ``_version`` argument to the :ref:`schedule.json` and :ref:`listspiders.json` webservices.
  - Add a ``jobid`` argument to the :ref:`schedule.json` webservice.
  - Add ``pid`` to the running jobs in the response from the :ref:`listjobs.json` webservice.
  - Include full tracebacks from Scrapy when failing to get spider list.
    This makes debugging deployment problems easier, but webservice output noisier.

- Website

  - Add a :ref:`webroot` setting for website root class.
  - Add start and finish times to jobs page.

- Make console script executable.
- Add contributing documentation.
- Twisted 16 support.
- Python 3 support.

Changed
~~~~~~~

- Change :ref:`bind_address` default to 127.0.0.1, instead of 0.0.0.0, to listen only for connections from localhost.

Removed
~~~~~~~

- Deprecate unused SQLite utilities in the ``scrapyd.sqlite`` module.

  - ``SqliteDict``
  - ``SqlitePickleDict``
  - ``SqlitePriorityQueue``
  - ``PickleSqlitePriorityQueue``

- Scrapy 0.x support.
- Python 2.6 support.

Fixed
~~~~~

- Poller race condition for concurrently accessed queues.

1.1.1 (2016-11-03)
------------------

Added
~~~~~

- Document and include missing settings in ``default_scrapyd.conf``.
- Document the spider queue's ``priority`` argument.
- Enable some missing tests for the SQLite queues.

Removed
~~~~~~~

- Disable bdist_wheel command in setup to define dynamic requirements, despite pip-7 wheel caching bug.

Fixed
~~~~~

- Use correct type adapter for sqlite3 blobs. In some systems, a wrong type adapter leads to incorrect buffer reads/writes.
- ``FEED_URI`` was always overridden by Scrapyd.
- Specify maximum versions for requirements that became incompatible.
- Mark package as zip-unsafe because Twistd requires a plain ``txapp.py``.

1.1.0 (2015-06-29)
------------------

Added
~~~~~

- Add ``node_name`` (hostname) to webservice responses. (:commit:`fac3a5c`, :commit:`4aebe1c`)
- Add ``start_time`` to the running jobs in the response from the :ref:`listjobs.json` webservice. (:commit:`6712af9`, :commit:`acd460b`)

Changed
~~~~~~~

- Move ``scrapyd-deploy`` command to `scrapyd-client <https://pypi.org/project/scrapyd-client/>`__ package. (:commit:`c1358dc`, :commit:`c9d66ca`, :commit:`191353e`)
- Allow the :ref:`items_dir` setting to be a URL. (:commit:`e261591`, :commit:`35a21db`)
- Look for a ``~/.scrapyd.conf`` file in the user's home directory. (:commit:`1fce99b`)

Fixed
~~~~~

- Check if a spider exists before scheduling it. (:issue:`8`, :commit:`288afef`, :commit:`a185ff2`)
- Sanitize version names when creating egg paths. (:commit:`8023720`)
- Generate correct feed URIs, using w3lib. (:commit:`9a88ea5`)
- Fix git versioning for projects without annotated tags. (:issue:`34`, :commit:`e91dcf4`)
- Use valid HTML markup on website pages. (:commit:`da5664f`, :commit:`26089cd`)
- Use ``file`` protocol for ``SCRAPY_FEED_URI`` environment variable on Windows. (:commit:`4f0060a`)
- Copy ``JsonResource`` class from Scrapy, which no longer provides it. (:commit:`99ea920`)
- Lowercase ``scrapyd`` package name. (:commit:`1adfc31`).
- Mark package as zip-unsafe, because Twisted requires a plain ``txapp.py``. (:commit:`f27c054`)
- Install scripts using ``entry_points`` instead of ``scripts``. (:commit:`b670f5e`)

1.0.2 (2016-03-28)
------------------

Fixed
~~~~~

- Mark package as zip-unsafe, because Twisted requires a plain ``txapp.py``.
- Specify maximum versions for compatible requirements.

1.0.1 (2013-09-02)
------------------

*Trivial update*

1.0.0 (2013-09-02)
------------------

First standalone release (it was previously shipped with Scrapy until Scrapy 0.16).
