RPM build documentation
-----------------------

+ Prerequisites to build rpm in general

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
  git clone https://github.com/scrapy/scrapyd.git scrapyd
  tar czvf scrapyd.tar.gz scrapyd
  cd ..
  cp SOURCES/scrapyd/centos/SPECS SPECS/scrapyd.spec 
  rpmbuild -ba ~/rpmbuild/SPECS/scrapyd.spec
```

$   
 


Pré-requis du RPM:
  pip install twisted
  pip install scrapy==0.18
  
  
A améliorer:
 - preinstall et preuninstall
 - man
 - dépendances



