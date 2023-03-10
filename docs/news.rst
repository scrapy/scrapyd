.. _news:

Release notes
=============

Unreleased
----------

Added
~~~~~

- Add ``spiderqueue`` configuration option for custom spider queue.

Changed
~~~~~~~

- ``scrapyd.spiderqueue.SqliteSpiderQueue`` is initialized with a ``scrapyd.config.Config`` object and a project name, rather than a SQLite connection string (i.e. database file path).
- If ``dbs_dir`` is set to ``:memory`` or to a URL, it is passed through without modification and without creating a directory to ``scrapyd.jobstorage.SqliteJobStorage`` and ``scrapyd.spiderqueue.SqliteSpiderQueue``.
- ``scrapyd.utils.get_spider_queues`` defers the creation of the ``dbs_dir`` directory to the spider queue implementation.

1.4.1 (2023-02-10)
------------------

Fixed
~~~~~

- Encode the ``FEEDS`` command-line argument as JSON.

1.4.0 (2023-02-07)
------------------

Added
~~~~~

- Add ``items_url`` and ``log_url`` to the response from the listjobs.json webservice. (@mxdev88)
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

  .. attention::

    These are undocumented and unused, and may be removed in future versions. If you use these environment variables, please `report your use in an issue <https://github.com/scrapy/scrapyd/issues>`__.

Removed
~~~~~~~

- Scrapy 1.x support.
- Python 3.6 support.
- Unmaintained files (Debian packaging) and unused code (``scrapyd/script.py``).

Fixed
~~~~~

- Print Scrapyd's version instead of Twisted's version with ``--version`` (``-v``) flag. (@niuguy)
- Override Scrapy's ``LOG_STDOUT`` setting to ``False`` to suppress logging output for listspiders.json webservice. (@Lucioric2000)

1.3.0 (2022-01-12)
------------------

Added
~~~~~

- Add support for HTTP authentication.
- Make ``project`` argument to listjobs.json optional, to easily query for all jobs.
- Improve HTTP headers across webservices.
- Add shortcut to jobs page to cancel a job using the cancel.json webservice.
- Add configuration options for job storage class and egg storage class.
- Improve test coverage.
- Python 3.7, 3.8, 3.9, 3.10 support.

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
- ``DeferredQueue`` no longer hides a pending job when reaching ``max_proc``.
- ``AddVersion``'s arguments' string types no longer break Windows environments.
- test: Update binary eggs to be compatible with Scrapy 1.x.

Removed
~~~~~~~

- Remove deprecated SQLite utilities.

1.2.0 (2017-04-12)
------------------

Added
~~~~~

- Webservice

  - Add daemonstatus.json webservice.
  - Add project version argument to the schedule.json webservice.
  - Add jobid argument to the schedule.json webservice.
  - Add the run's PID to the response of the listjobs.json webservice.
  - Include full tracebacks from Scrapy when failing to get spider list.
    This makes debugging deployment problems easier, but webservice output noisier.

- Website

  - Add ``webroot`` configuration option for website root class.
  - Add start and finish times to jobs page.

- Make console script executable.
- Add contributing documentation.
- Twisted 16 support.
- Python 3 support.

Changed
~~~~~~~

- Change ``bind_address`` default to 127.0.0.1, instead of 0.0.0.0, to listen only for connections from localhost.

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

- Document and include missing configuration options in ``default_scrapyd.conf``.
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
- Add ``start_time`` to the response from the listjobs.json webservice. (:commit:`6712af9`, :commit:`acd460b`)

Changed
~~~~~~~

- Move scrapyd-deploy command to `scrapyd-client <https://pypi.org/project/scrapyd-client/>`__ package. (:commit:`c1358dc`, :commit:`c9d66ca`, :commit:`191353e`)
- Allow remote ``items_dir`` configuration. (:commit:`e261591`, :commit:`35a21db`)
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
