.. _news:

Release notes
=============

1.3.0
-----
*Unreleased*

Added
~~~~~

- Jobs website shortcut to cancel a job using the cancel.json webservice.
- Make project argument to listjobs.json optional,
  so that we can easily query for all jobs.
- Python 3.7, 3.8 and 3.9 support

Removed
~~~~~~~

- Doc for ubunut installs removed. Scrapinghub no longer maintains ubuntu repo.
- Python 3.3 support (although never officially supported)
- Python 3.4 support
- Pypy 2 support

1.2.1
-----
*Release date: 2019-06-17*

Fixed
~~~~~
- http header types were breaking newer twisted versions
- DeferredQueue was hiding a pending job when reaching max_proc
- AddVersion's arguments' string types were breaking the environment in windows
- Tests: Updated binary eggs to be scrapy-1.x compatible

1.2.0
-----
*Release date: 2017-04-12*

The highlight of this release is the long-awaited Python 3 support.

The new scrapy requirement is version 1.0 or higher.
Python 2.6 is no longer supported by scrapyd.

Some unused sqlite utilities are now deprecated
and will be removed from a later scrapyd release.
Instantiating them or subclassing from them
will trigger a deprecation warning.
These are located under ``scrapyd.sqlite``:

- SqliteDict
- SqlitePickleDict
- SqlitePriorityQueue
- PickleSqlitePriorityQueue

Added
~~~~~

- Include run's PID in listjobs webservice.
- Include full tracebacks from scrapy when failing to get spider list.
  This will lead to more noisy webservice output
  but will make debugging deployment problems much easier.
- Include start/finish time in daemon's joblist page
- Twisted 16 compatibility
- Python 3 compatibility
- Make console script executable
- Project version argument in the schedule webservice
- Configuration option for website root class
- Optional jobid argument to schedule webservice
- Contribution documentation
- Daemon status webservice

Removed
~~~~~~~

- scrapyd's bind_address now defaults to 127.0.0.1 instead of 0.0.0.0
  to listen only for connection from the local host
- scrapy < 1.0 compatibility
- python < 2.7 compatibility

Fixed
~~~~~

- Poller race condition for concurrently accessed queues

1.1.1
-----
*Release date: 2016-11-03*

Removed
~~~~~~~

- Disabled bdist_wheel command in setup to define dynamic requirements
  despite of pip-7 wheel caching bug.

Fixed
~~~~~

- Use correct type adapter for sqlite3 blobs.
  In some systems, a wrong type adapter leads to incorrect buffer reads/writes.
- FEED_URI was always overridden by scrapyd
- Specified maximum versions for requirements that became incompatible.
- Marked package as zip-unsafe because twistd requires a plain ``txapp.py``
- Don't install zipped scrapy in py26 CI env
  because its setup doesn't include the ``scrapy/VERSION`` file.

Added
~~~~~

- Enabled some missing tests for the sqlite queues.
- Enabled CI tests for python2.6 because it was supported by the 1.1 release.
- Document missing config options and include in default_scrapyd.conf
- Note the spider queue's ``priority`` argument in the scheduler's doc.


1.1.0
-----
*Release date: 2015-06-29*

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

1.0.2
-----
*Release date: 2016-03-28*

setup script
~~~~~~~~~~~~

- Specified maximum versions for requirements that became incompatible.
- Marked package as zip-unsafe because twistd requires a plain ``txapp.py``

documentation
~~~~~~~~~~~~~

- Updated broken links, references to wrong versions and scrapy
- Warn that scrapyd 1.0 felling out of support

1.0.1
-----
*Release date: 2013-09-02*
*Trivial update*

1.0.0
-----
*Release date: 2013-09-02*

First standalone release (it was previously shipped with Scrapy until Scrapy 0.16).
