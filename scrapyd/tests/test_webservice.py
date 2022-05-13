from pathlib import Path
from unittest import mock

from scrapyd.interfaces import IEggStorage


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

    def test_delete_version(self, txrequest, site_with_egg):
        endpoint = b'delversion.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
            b'version': [b'0.1']
        }

        storage = site_with_egg.app.getComponent(IEggStorage)
        egg = storage.get('quotesbot')
        assert egg[0] is not None
        content = site_with_egg.children[endpoint].render_POST(txrequest)
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert storage.get('quotesbot')
        no_egg = storage.get('quotesbot')
        assert no_egg[0] is None

    def test_delete_project(self, txrequest, site_with_egg):
        endpoint = b'delproject.json'
        txrequest.args = {
            b'project': [b'quotesbot'],
        }

        storage = site_with_egg.app.getComponent(IEggStorage)
        egg = storage.get('quotesbot')
        assert egg[0] is not None

        content = site_with_egg.children[endpoint].render_POST(txrequest)
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert storage.get('quotesbot')
        no_egg = storage.get('quotesbot')
        assert no_egg[0] is None

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
        egg = storage.get('quotesbot')
        assert egg[0] is None

        content = site_no_egg.children[endpoint].render_POST(txrequest)
        assert content['status'] == 'ok'
        assert 'node_name' in content
        assert storage.get('quotesbot')
        no_egg = storage.get('quotesbot')
        assert no_egg[0] == '0_1'

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
