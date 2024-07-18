from pathlib import Path
from unittest import mock

import pytest
<<<<<<< HEAD
from twisted.web.error import Error

||||||| parent of 9e4eccd (test: Add tests to tests/test_webservice.py for directory traversal)
=======

from scrapyd.exceptions import DirectoryTraversalError, RunnerError
>>>>>>> 9e4eccd (test: Add tests to tests/test_webservice.py for directory traversal)
from scrapyd.interfaces import IEggStorage
from scrapyd.jobstorage import Job


def fake_list_jobs(*args, **kwargs):
    yield Job('proj1', 'spider-a', 'id1234')


def fake_list_spiders(*args, **kwargs):
    return []


def fake_list_spiders_other(*args, **kwarsg):
    return ['quotesbot', 'toscrape-css']


class TestWebservice:
    @mock.patch('scrapyd.webservice.get_spider_list', new=fake_list_spiders)
    def test_list_spiders(self, txrequest, site_no_egg):
        # TODO Test with actual egg requires to write better mock runner
        # scrapyd webservice calls subprocess with command
        # "python -m scrapyd.runner list", need to write code to mock this
        # and test it
        txrequest.args = {
            b'project': [b'quotesbot']
        }
        endpoint = b'listspiders.json'
        content = site_no_egg.children[endpoint].render_GET(txrequest)

        assert content['spiders'] == []
        assert content['status'] == 'ok'

    def test_list_versions(self, txrequest, site_with_egg):
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'spider': [b'toscrape-css']
        }
        endpoint = b'listversions.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)

        assert content['versions'] == ['0_1']
        assert content['status'] == 'ok'

    def test_list_projects(self, txrequest, site_with_egg):
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'spider': [b'toscrape-css']
        }
        endpoint = b'listprojects.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)

        assert content['projects'] == ['quotesbot']

    def test_list_jobs(self, txrequest, site_with_egg):
        txrequest.args = {}
        endpoint = b'listjobs.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)

        assert set(content) == {'node_name', 'status', 'pending', 'running', 'finished'}

    @mock.patch('scrapyd.jobstorage.MemoryJobStorage.__iter__', new=fake_list_jobs)
    def test_list_jobs_finished(self, txrequest, site_with_egg):
        txrequest.args = {}
        endpoint = b'listjobs.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)

        assert set(content['finished'][0]) == {
            'project', 'spider', 'id', 'start_time', 'end_time', 'log_url', 'items_url'
        }

    def test_delete_version(self, txrequest, site_with_egg):
        endpoint = b'delversion.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'version': [b'0.1']
        }

        storage = site_with_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        content = site_with_egg.children[endpoint].render_POST(txrequest)
        no_version, no_egg = storage.get('quotesbot')
        if no_egg:
            no_egg.close()

        assert version is not None
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert no_version is None

    def test_delete_project(self, txrequest, site_with_egg):
        endpoint = b'delproject.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
        }

        storage = site_with_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        content = site_with_egg.children[endpoint].render_POST(txrequest)
        no_version, no_egg = storage.get('quotesbot')
        if no_egg:
            no_egg.close()

        assert version is not None
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert no_version is None

    @mock.patch('scrapyd.webservice.get_spider_list', new=fake_list_spiders)
    def test_addversion(self, txrequest, site_no_egg):
        endpoint = b'addversion.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'version': [b'0.1']
        }
        egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
        with open(egg_path, 'rb') as f:
            txrequest.args[b'egg'] = [f.read()]

        storage = site_no_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        content = site_no_egg.children[endpoint].render_POST(txrequest)
        no_version, no_egg = storage.get('quotesbot')
        if no_egg:
            no_egg.close()

        assert version is None
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert no_version == '0_1'

    @mock.patch('scrapyd.webservice.get_spider_list',
                new=fake_list_spiders_other)
    def test_schedule(self, txrequest, site_with_egg):
        endpoint = b'schedule.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'spider': [b'toscrape-css']
        }

        content = site_with_egg.children[endpoint].render_POST(txrequest)

        assert site_with_egg.scheduler.calls == [['quotesbot', 'toscrape-css']]
        assert content['status'] == 'ok'
        assert 'jobid' in content

    def test_schedule_bad_request(self, txrequest, site_with_egg):
        endpoint = b'schedule.json'
        txrequest.args = {
            b'project': [b'/etc/host/quotesbot'],
            b'spider': [b'toscrape-css']
        }

        with pytest.raises(Error) as e:
            site_with_egg.children[endpoint].render_POST(txrequest)

            assert e.args[0] == 400

        assert site_with_egg.scheduler.calls == []

    @pytest.mark.parametrize('endpoint,attach_egg,method', [
        (b'schedule.json', False, 'render_POST'),
        (b'cancel.json', False, 'render_POST'),
        (b'addversion.json', True, 'render_POST'),
        (b'listversions.json', False, 'render_GET'),
        (b'listspiders.json', False, 'render_GET'),
        (b'status.json', False, 'render_GET'),
        (b'listjobs.json', False, 'render_GET'),
        (b'delproject.json', False, 'render_POST'),
        (b'delversion.json', False, 'render_POST'),
    ])
    def test_bad_project_names_invalid(self, txrequest, site_no_egg, endpoint, attach_egg, method):
        txrequest.args = {
            b'project': [b'/home/pawel/hosts'],
            b'version': [b'0.1'],
            b'job': [b'abc'],
        }

        if attach_egg:
            egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
            with open(egg_path, 'rb') as f:
                txrequest.args[b'egg'] = [f.read()]

        with pytest.raises(Error) as e:
            getattr(site_no_egg.children[endpoint], method)(txrequest)

        assert e.value.status == b'400'
        assert e.value.message == b"project '/home/pawel/hosts' is invalid"

        storage = site_no_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        assert version is None

    @pytest.mark.parametrize('endpoint,attach_egg,method', [
        (b'addversion.json', True, 'render_POST'),
        (b'listversions.json', False, 'render_GET'),
        (b'delproject.json', False, 'render_POST'),
        (b'delversion.json', False, 'render_POST'),
    ])
    def test_bad_project_names(self, txrequest, site_no_egg, endpoint, attach_egg, method):
        txrequest.args = {
            b'project': [b'../p'],
            b'version': [b'0.1'],
        }

        if attach_egg:
            egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
            with open(egg_path, 'rb') as f:
                txrequest.args[b'egg'] = [f.read()]

        with pytest.raises(DirectoryTraversalError) as exc:
            getattr(site_no_egg.children[endpoint], method)(txrequest)

        assert str(exc.value) == "../p"

        storage = site_no_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        assert version is None

    @pytest.mark.parametrize('endpoint,attach_egg,method', [
        (b'schedule.json', False, 'render_POST'),
        (b'listspiders.json', False, 'render_GET'),
    ])
    def test_bad_project_names_runner(self, txrequest, site_no_egg, endpoint, attach_egg, method):
        txrequest.args = {
            b'project': [b'../p'],
            b'spider': [b's'],
        }

        if attach_egg:
            egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
            with open(egg_path, 'rb') as f:
                txrequest.args[b'egg'] = [f.read()]

        with pytest.raises(RunnerError) as exc:
            getattr(site_no_egg.children[endpoint], method)(txrequest)

        assert str(exc.value).startswith("Traceback (most recent call last):"), str(exc.value)
        assert str(exc.value).endswith("scrapyd.exceptions.DirectoryTraversalError: ../p\n"), str(exc.value)

        storage = site_no_egg.app.getComponent(IEggStorage)
        version, egg = storage.get('quotesbot')
        if egg:
            egg.close()

        assert version is None
