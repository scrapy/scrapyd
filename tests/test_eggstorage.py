from io import BytesIO
from unittest.mock import patch

import pytest
from twisted.trial import unittest
from zope.interface import implementer
from zope.interface.verify import verifyObject

from scrapyd.app import application
from scrapyd.config import Config
from scrapyd.eggstorage import FilesystemEggStorage, sorted_versions
from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEggStorage


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


@implementer(IEggStorage)
class SomeFakeEggStorage:
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


class TestConfigureEggStorage(unittest.TestCase):
    def test_egg_config_application(self):
        config = Config()
        eggstore = "tests.test_eggstorage.SomeFakeEggStorage"
        config.cp.set("scrapyd", "eggstorage", eggstore)
        app = application(config)
        app_eggstorage = app.getComponent(IEggStorage)

        self.assertIsInstance(app_eggstorage, SomeFakeEggStorage)
        self.assertEqual(app_eggstorage.list_projects(), ["hello_world"])


class EggStorageTest(unittest.TestCase):
    def setUp(self):
        d = self.mktemp()
        config = Config(values={"eggs_dir": d})
        self.eggst = FilesystemEggStorage(config)

    def test_interface(self):
        verifyObject(IEggStorage, self.eggst)

    def test_put_secure(self):
        with pytest.raises(DirectoryTraversalError) as exc:
            self.eggst.put(BytesIO(b"egg01"), "../p", "v")  # version is sanitized

        self.assertEqual(str(exc.value), "../p")

    def test_get_secure(self):
        with pytest.raises(DirectoryTraversalError) as exc:
            self.eggst.get("../p", "v")  # version is sanitized

        self.assertEqual(str(exc.value), "../p")

    def test_list_secure_join(self):
        with pytest.raises(DirectoryTraversalError) as exc:
            self.eggst.list("../p")

        self.assertEqual(str(exc.value), "../p")

    def test_list_secure_glob(self):
        self.eggst.put(BytesIO(b"egg01"), "mybot", "01")
        versions = self.eggst.list("*")

        self.eggst.delete("mybot")
        self.assertEqual(versions, [])  # ['01'] if * not escaped

    def test_delete(self):
        with pytest.raises(DirectoryTraversalError) as exc:
            self.eggst.delete("../p", "v")  # version is sanitized

        self.assertEqual(str(exc.value), "../p")

    @patch("scrapyd.eggstorage.glob", new=lambda x: ["ddd", "abc", "bcaa"])
    def test_list_hashes(self):
        versions = self.eggst.list("any")

        self.assertEqual(versions, ["abc", "bcaa", "ddd"])

    @patch("scrapyd.eggstorage.glob", new=lambda x: ["9", "2", "200", "3", "4"])
    def test_list_semantic_versions(self):
        versions = self.eggst.list("any")

        self.assertEqual(versions, ["2", "3", "4", "9", "200"])

    def test_put_get_list_delete(self):
        self.eggst.put(BytesIO(b"egg01"), "mybot", "01")
        self.eggst.put(BytesIO(b"egg03"), "mybot", "03/ver")
        self.eggst.put(BytesIO(b"egg02"), "mybot", "02_my branch")

        self.assertEqual(self.eggst.list("mybot"), ["01", "02_my_branch", "03_ver"])
        self.assertEqual(self.eggst.list("mybot2"), [])

        v, f = self.eggst.get("mybot")
        try:
            self.assertEqual(v, "03_ver")
            self.assertEqual(f.read(), b"egg03")
        finally:
            f.close()

        v, f = self.eggst.get("mybot", "02_my branch")
        try:
            self.assertEqual(v, "02_my branch")
            self.assertEqual(f.read(), b"egg02")
        finally:
            f.close()

        v, f = self.eggst.get("mybot", "02_my_branch")
        try:
            self.assertEqual(v, "02_my_branch")
            self.assertEqual(f.read(), b"egg02")
        finally:
            f.close()

        self.eggst.delete("mybot", "02_my branch")
        self.assertEqual(self.eggst.list("mybot"), ["01", "03_ver"])

        self.eggst.delete("mybot", "03_ver")
        self.assertEqual(self.eggst.list("mybot"), ["01"])

        self.eggst.delete("mybot")
        self.assertEqual(self.eggst.list("mybot"), [])
