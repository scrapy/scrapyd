.. _news:

Release notes
=============

1.1.0
-----

Features & Enhancements
~~~~~~~~~~~~~~~~~~~~~~~

- Outsource scrapyd-deploy command to scrapyd-client (#92, #90)
- Look for a .scrapyd.conf file in the users home (~/.scrapyd.conf) (#58)
- Adding the nodename to identify the process that is working on the job (#42)
- Allow remote items store (#48)
- Debian sysvinit script (#41)
- Add 'start_time' field in webservice for running jobs (#24)

Bugfixes
~~~~~~~~

- Updating integration test script (#98)
- Changed scripts to be installed using entry_points (#89)
- Fix bug with --list-projects option in scrapyd-deploy (#88)
- Update api.rst (#79)
- Renovate scrapy upstart job a bit (#57)
- Sanitize version names when creating egg paths (#72)
- Use w3lib to generate feed uris (#73)
- Copy txweb/JsonResource import from scrapy (#62)
- Travis.yml: remove deprecated --use-mirros pip option (b3cdc61)
- Make scrapyd package zip unsafe because the scrapyd command requires the txapp.py unpacked to run (f27c054, #49)
- Check if a spider exists before schedule it (with sqlite cache) (#8, #17)
- Fixing typo "mulitplied" (#51)
- Fix GIT versioning for projects without annotated tags (#47)
- Fix release notes: 1.0 is already released (6c8dcfb)
- Correcting HTML tags in scrapyd website monitor (#38)
- Update index.rst (#37)
- Added missing anchor closing tags (#35)
- Removed python 2.6/lucid env from travis (#32)
- Changed the links to the new documentation page (#33)
- Fix (at least) windows problem (#19)
- Remove reference to 'scrapy server' command (f599b60, #25)
- Made Scrapyd package name lowercase (1adfc31)

1.0.2
-----

setup script
~~~~~~~~~~~~

- Specified maximum versions for requirements that became incompatible.
- Marked package as zip-unsafe because twistd requires a plain ``txapp.py``

documentation
~~~~~~~~~~~~~

- Updated broken links, references to wrong versions and scrapy
- Warn that scrapyd 1.0 felling out of support

1.0
---

First standalone release (it was previously shipped with Scrapy until Scrapy 0.16).
