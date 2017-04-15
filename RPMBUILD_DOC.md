RPM build documentation
-----------------------

+ Prerequisites to build rpms in general

Install build packages
```bash
  yum groupinstall "Fedora Packager"
```

Create build user and environment
```bash
  useradd builder
  passwd builder
  su - builder
  rpmdev-setuptree
```

+ Build rpm for scrapyd

As the build user in its home, clone scrapyd in the SOURCES dir:
```bash
  cd rpmbuild/SOURCES
  git clone https://github.com/scrapy/scrapyd.git scrapyd   # or https://github.com/medialab/scrapyd.git until pull request included
  tar czvf scrapyd.tar.gz scrapyd
  cd ..
  cp SOURCES/scrapyd/centos/SPECS SPECS/scrapyd.spec 
  rpmbuild -ba ~/rpmbuild/SPECS/scrapyd.spec
```

Collect the package rpm in rpmbuild/RPMS/ and the source rpm in rpmbuild/SRPMS/ and publish in online repository.
