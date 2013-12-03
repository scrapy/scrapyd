=======================
RPM build documentation
=======================

Prerequisites to build rpms in general
--------------------------------------
 
Install build packages:

.. code-block:: bash

  sudo yum groupinstall "Fedora Packager"

Create build user:

.. code-block:: bash

  sudo useradd builder
  sudo passwd builder

As build user, create building environment:

.. code-block:: bash

  sudo su - builder
  rpmdev-setuptree


Build rpm for scrapyd
---------------------

As build user in its home, clone scrapyd in the SOURCES dir:

.. code-block:: bash

  cd rpmbuild/SOURCES
  git clone https://github.com/scrapy/scrapyd.git scrapyd
  tar czvf scrapyd.tar.gz scrapyd
  cp scrapyd/centos/SPECS ../SPECS/scrapyd.spec
  rpmbuild -ba ~/rpmbuild/SPECS/scrapyd.spec

Collect the package rpm in rpmbuild/RPMS/ and the source rpm in rpmbuild/SRPMS/ and publish in online repository.

