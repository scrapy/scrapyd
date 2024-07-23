import io
import os.path
from contextlib import closing

import pytest
from zope.interface import implementer
from zope.interface.verify import verifyObject

from scrapyd.app import application
from scrapyd.config import Config
from scrapyd.eggstorage import FilesystemEggStorage, sorted_versions
from scrapyd.exceptions import DirectoryTraversalError, EggNotFoundError, ProjectNotFoundError
from scrapyd.interfaces import IEggStorage


@implementer(IEggStorage)
class MockEggStorage:
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
        # letter
        (["zzz", "b", "ddd", "a", "x"], ["a", "b", "ddd", "x", "zzz"]),
        # number
        (["10", "1", "9"], ["1", "9", "10"]),
        # "r" number
        (["r10", "r1", "r9"], ["r1", "r10", "r9"]),
        # version
        (["2.11", "2.01", "2.9"], ["2.01", "2.9", "2.11"]),
        # number and letter
        (["123456789", "b3b8fd2"], ["123456789", "b3b8fd2"]),
    ],
)
def test_sorted_versions(versions, expected):
    assert sorted_versions(versions) == expected


def test_config(chdir):
    config = Config()
    config.cp.set("scrapyd", "eggstorage", "tests.test_eggstorage.MockEggStorage")

    app = application(config)
    eggstorage = app.getComponent(IEggStorage)

    assert isinstance(eggstorage, MockEggStorage)
    assert eggstorage.list_projects() == ["hello_world"]


def test_interface(eggstorage):
    verifyObject(IEggStorage, eggstorage)


def test_put_secure(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.put(io.BytesIO(b"data"), "../p", "v")  # version is sanitized

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
    eggstorage.put(io.BytesIO(b"data"), "mybot", "01")

    assert eggstorage.list("*") == []  # ["01"] if * weren't escaped


def test_delete_secure(eggstorage):
    with pytest.raises(DirectoryTraversalError) as exc:
        eggstorage.delete("../p", "v")  # version is sanitized

    assert str(exc.value) == "../p"


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, (None, None)),
        ("nonexistent", (None, None)),
        ("01", (None, None)),
    ],
)
def test_get_empty(eggstorage, version, expected):
    assert eggstorage.get("mybot", version) == expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, ("03", b"egg03")),
        ("nonexistent", (None, None)),
        ("01", ("01", b"egg01")),
    ],
)
def test_get_many(eggstorage, version, expected):
    eggstorage.put(io.BytesIO(b"egg01"), "mybot", "01")
    eggstorage.put(io.BytesIO(b"egg03"), "mybot", "03")
    eggstorage.put(io.BytesIO(b"egg02"), "mybot", "02")

    version, data = eggstorage.get("mybot", version)
    if data is not None:
        with closing(data):
            data = data.read()

    assert (version, data) == expected


@pytest.mark.parametrize(
    ("versions", "expected"),
    [(["ddd", "abc", "bcaa"], ["abc", "bcaa", "ddd"]), (["9", "2", "200", "3", "4"], ["2", "3", "4", "9", "200"])],
)
def test_list(eggstorage, versions, expected):
    assert eggstorage.list("mybot") == []

    for version in versions:
        eggstorage.put(io.BytesIO(b"egg01"), "mybot", version)

    assert eggstorage.list("mybot") == expected


def test_list_glob(eggstorage):
    directory = os.path.join(eggstorage.basedir, "mybot")
    os.makedirs(directory)
    with open(os.path.join(directory, "other"), "wb") as f:
        f.write(b"")

    assert eggstorage.list("mybot") == []  # "other" without "*.egg" glob


def test_list_projects(eggstorage):
    with open(os.path.join(eggstorage.basedir, "other"), "wb") as f:
        f.write(b"")

    assert eggstorage.list_projects() == []  # "other" without isdir() filter

    eggstorage.put(io.BytesIO(b"egg01"), "mybot", "01")

    assert eggstorage.list_projects() == ["mybot"]


def test_delete_project(eggstorage):
    eggstorage.put(io.BytesIO(b"egg01"), "mybot", "01")
    eggstorage.put(io.BytesIO(b"egg03"), "mybot", "03")
    eggstorage.put(io.BytesIO(b"egg02"), "mybot", "02")

    assert eggstorage.list("mybot") == ["01", "02", "03"]

    eggstorage.delete("mybot")

    assert eggstorage.list("mybot") == []


def test_delete_vesrion(eggstorage):
    eggstorage.put(io.BytesIO(b"egg01"), "mybot", "01")
    eggstorage.put(io.BytesIO(b"egg03"), "mybot", "03")
    eggstorage.put(io.BytesIO(b"egg02"), "mybot", "02")

    assert eggstorage.list("mybot") == ["01", "02", "03"]

    eggstorage.delete("mybot", "02")

    assert eggstorage.list("mybot") == ["01", "03"]

    eggstorage.delete("mybot", "03")

    assert eggstorage.list("mybot") == ["01"]

    eggstorage.delete("mybot", "01")

    assert eggstorage.list("mybot") == []
    assert not os.path.exists(os.path.join(eggstorage.basedir, "mybot"))


def test_delete_nonexistent_project(eggstorage):
    with pytest.raises(ProjectNotFoundError):
        eggstorage.delete("mybot")


def test_delete_nonexistent_version(eggstorage):
    with pytest.raises(EggNotFoundError):
        eggstorage.delete("mybot", "01")

    eggstorage.put(io.BytesIO(b"egg01"), "mybot", "01")

    with pytest.raises(EggNotFoundError):
        eggstorage.delete("mybot", "02")
