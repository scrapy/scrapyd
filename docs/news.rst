.. _news:

Release notes
=============

1.1.1
-----
*Release date: 2016-11-03*

Removed
~~~~~~~

- Disabled bdist_wheel command in setup to define dynamic requirements
  despite of pip-7 wheel caching bug.

Fixed
~~~~~

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
