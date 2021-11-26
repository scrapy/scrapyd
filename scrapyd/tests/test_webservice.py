from pathlib import Path

import pytest
from twisted.web.error import Error

from scrapyd.interfaces import IEggStorage


class TestWebservice:
    def test_list_spiders(self, txrequest, site_with_egg):
        txrequest.args = {
            b'project': [b'quotesbot']
        }
        expected = {
            'node_name': 'computer',
            'spiders': ['toscrape-css', 'toscrape-xpath'],
            'status': 'ok'
        }
        endpoint = b'listspiders.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)
        assert content == expected

    def test_list_versions(self, txrequest, site_with_egg):
        txrequest.args = {b'project': [b'quotesbot'],
                          b'spider': [b'toscrape-css']}
        expected = {
            'node_name': 'computer',
            'versions': ['0_1'],
            'status': 'ok'
        }
        endpoint = b'listversions.json'
        content = site_with_egg.children[endpoint].render_GET(txrequest)
        assert content == expected

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

    def test_delete_project_bad_project_name(self, txrequest, site_with_egg):
        endpoint = b'delproject.json'
        txrequest.args = {
            b'project': [b'/etc/hosts/'],
            b'version': [b'0.1']
        }
        with pytest.raises(Error) as e:
            site_with_egg.children[endpoint].render_POST(txrequest)
            assert e.args[0] == 400

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
