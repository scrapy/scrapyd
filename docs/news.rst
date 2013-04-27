.. _news:

Release notes
=============

0.18.0 (unreleased)
-------------------

- forked out of Scrapy

0.16.0 (released 2012-10-18)
----------------------------

Scrapyd changes:

- New Scrapyd API methods: :ref:`listjobs.json` and :ref:`cancel.json`
- New Scrapyd settings: :ref:`items_dir` and :ref:`jobs_to_keep`
- Items are now stored on disk using feed exports, and accessible through the Scrapyd web interface
- Support making Scrapyd listen into a specific IP address (see ``bind_address`` option)
