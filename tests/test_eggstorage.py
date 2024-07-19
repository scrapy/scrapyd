from io import BytesIO
from unittest.mock import patch

import pytest
from zope.interface import implementer
from zope.interface.verify import verifyObject

from scrapyd.app import application
from scrapyd.config import Config
from scrapyd.eggstorage import FilesystemEggStorage, sorted_versions
from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEggStorage


@implementer(IEggStorage)
class FakeEggStorage:
    def __init__(self, config):
        self.config = config

    def put(self, eggfile, project, version):
        pass

    def get(self, project, version=None):
        pass

    def list(self, project):
        pass

    def list_projects(self):
        return ["hello_world"]

    def delete(self, project, version=None):
        pass


@pytest.fixture()
def eggstorage(tmpdir):
    return FilesystemEggStorage(Config(values={"eggs_dir": tmpdir}))


@pytest.mark.parametrize(
    ("versions", "expected"),
    [
        (["zzz", "b", "ddd", "a", "x"], ["a", "b", "ddd", "x", "zzz"]),
        (["10", "1", "9"], ["1", "9", "10"]),
        (["2.11", "2.01", "2.9"], ["2.01", "2.9", "2.11"]),
    ],
)
def test_sorted_versions(versions, expected):
    assert sorted_versions(versions) == expected


def test_egg_config_application():
    config = Config()
    eggstore = "tests.test_eggstorage.FakeEggStorage"
    config.cp.set("scrapyd", "eggstorage", eggstore)
    app = application(config)
    app_eggstorage = app.getComponent(IEggStorage)

    assert isinstance(app_eggstorage, FakeEggStorage)
    assert app_eggstorage.list_projects() == ["hello_world"]


def test_interface(eggstorage):
    verifyObject(IEggStorage, eggstorage)


def test_put_secure(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.put(BytesIO(b"egg01"), "../p", "v")  # version is sanitized

    assert str(exc.value) == "../p"


def test_get_secure(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.get("../p", "v")  # version is sanitized

    assert str(exc.value) == "../p"


def test_list_secure_join(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.list("../p")

    assert str(exc.value) == "../p"


def test_list_secure_glob(eggstorage):
    eggstorage.put(BytesIO(b"egg01"), "mybot", "01")
    versions = eggstorage.list("*")

    eggstorage.delete("mybot")
    assert versions == []  # ['01'] if * not escaped


def test_delete(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.delete("../p", "v")  # version is sanitized

    assert str(exc.value) == "../p"


@patch("scrapyd.eggstorage.glob", new=lambda x: ["ddd", "abc", "bcaa"])
def test_list_hashes(eggstorage):
    versions = eggstorage.list("any")

    assert versions == ["abc", "bcaa", "ddd"]


@patch("scrapyd.eggstorage.glob", new=lambda x: ["9", "2", "200", "3", "4"])
def test_list_semantic_versions(eggstorage):
    versions = eggstorage.list("any")

    assert versions == ["2", "3", "4", "9", "200"]


def test_put_get_list_delete(eggstorage):
    eggstorage.put(BytesIO(b"egg01"), "mybot", "01")
    eggstorage.put(BytesIO(b"egg03"), "mybot", "03/ver")
    eggstorage.put(BytesIO(b"egg02"), "mybot", "02_my branch")

    assert eggstorage.list("mybot") == ["01", "02_my_branch", "03_ver"]
    assert eggstorage.list("mybot2") == []

    v, f = eggstorage.get("mybot")
    try:
        assert v == "03_ver"
        assert f.read() == b"egg03"
    finally:
        f.close()

    v, f = eggstorage.get("mybot", "02_my branch")
    try:
        assert v == "02_my branch"
        assert f.read() == b"egg02"
    finally:
        f.close()

    v, f = eggstorage.get("mybot", "02_my_branch")
    try:
        assert v == "02_my_branch"
        assert f.read() == b"egg02"
    finally:
        f.close()

    eggstorage.delete("mybot", "02_my branch")
    assert eggstorage.list("mybot") == ["01", "03_ver"]

    eggstorage.delete("mybot", "03_ver")
    assert eggstorage.list("mybot") == ["01"]

    eggstorage.delete("mybot")
    assert eggstorage.list("mybot") == []
