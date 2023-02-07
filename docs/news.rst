.. _news:

Release notes
=============

1.4.0 (2023-02-07)
------------------

Added
~~~~~

- Add ``item_url`` and ``log_url`` to the response from the listjobs.json webservice. (@mxdev88)
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

Features & Enhancements
~~~~~~~~~~~~~~~~~~~~~~~

- Outsource scrapyd-deploy command to scrapyd-client (c1358dc, c9d66ca..191353e)
  **If you rely on this command, install the scrapyd-client package from pypi.**
- Look for a ``~/.scrapyd.conf`` file in the users home (1fce99b)
- Adding the nodename to identify the process that is working on the job (fac3a5c..4aebe1c)
- Allow remote items store (e261591..35a21db)
- Debian sysvinit script (a54193a, ff457a9)
- Add 'start_time' field in webservice for running jobs (6712af9, acd460b)
- Check if a spider exists before schedule it (with sqlite cache) (#8, 288afef..a185ff2)

Bugfixes
~~~~~~~~

- F̶i̶x̶ ̶s̶c̶r̶a̶p̶y̶d̶-̶d̶e̶p̶l̶o̶y̶ ̶-̶-̶l̶i̶s̶t̶-̶p̶r̶o̶j̶e̶c̶t̶s̶ ̶(̶9̶4̶2̶a̶1̶b̶2̶)̶ → moved to scrapyd-client
- Sanitize version names when creating egg paths (8023720)
- Copy txweb/JsonResource from scrapy which no longer provides it (99ea920)
- Use w3lib to generate correct feed uris (9a88ea5)
- Fix GIT versioning for projects without annotated tags (e91dcf4 #34)
- Correcting HTML tags in scrapyd website monitor (da5664f, 26089cd)
- Fix FEED_URI path on windows (4f0060a)

Setup script and Tests/CI
~~~~~~~~~~~~~~~~~~~~~~~~~

- Restore integration test script (66de25d)
- Changed scripts to be installed using entry_points (b670f5e)
- Renovate scrapy upstart job (d130770)
- Travis.yml: remove deprecated ``--use-mirros`` pip option (b3cdc61)
- Mark package as zip unsafe because twistd requires a plain ``txapp.py`` (f27c054)
- Removed python 2.6/lucid env from travis (5277755)
- Made Scrapyd package name lowercase (1adfc31)

Documentation
~~~~~~~~~~~~~

- Spiders should allow for arbitrary keyword arguments (696154)
- Various typos (51f1d69, 0a4a77a)
- Fix release notes: 1.0 is already released (6c8dcfb)
- Point website module's links to readthedocs (215c700)
- Remove reference to 'scrapy server' command (f599b60)

1.0.2 (2016-03-28)
------------------

setup script
~~~~~~~~~~~~

- Specified maximum versions for requirements that became incompatible.
- Marked package as zip-unsafe because twistd requires a plain ``txapp.py``

documentation
~~~~~~~~~~~~~

- Updated broken links, references to wrong versions and scrapy
- Warn that scrapyd 1.0 felling out of support

1.0.1 (2013-09-02)
------------------

*Trivial update*

1.0.0 (2013-09-02)
------------------

First standalone release (it was previously shipped with Scrapy until Scrapy 0.16).
