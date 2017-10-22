import base64
import json
import lzma
import os
from pathlib import Path

from airtable import Airtable
import requests
import pytest

from airtable_local_backup import download

HERE = os.path.dirname(__file__)


@pytest.fixture
def lots_of_fields_raw():
    with open(Path(HERE, 'lots_of_fields_raw.json'), 'r') as jsonfile:
        return json.load(jsonfile)
    # return fake_tabledata


@pytest.fixture
def lots_of_fields_hashes():
    with open(Path(HERE, 'hashes.json'), 'r') as jsonfile:
        return json.load(jsonfile)


@pytest.fixture
def filedata():
    with open(Path(HERE, 'filedata.json'), 'r') as jsonfile:
        return json.load(jsonfile)


@pytest.fixture
def lots_of_fields_correct():
    with Path(HERE, 'lots_of_fields.json').open(mode='r') as jsonfile:
        return json.load(jsonfile)


def rettrue(*args):
    return True


def test_download_table(lots_of_fields_raw, lots_of_fields_hashes,
                        monkeypatch, filedata, lots_of_fields_correct):
    def get_attach_patched(url):
        class FakeDownload():
            def __init__(self, data):
                self.content = data.encode('utf-8')
        return FakeDownload(filedata[url])

    def get_table_data(*args):
        return lots_of_fields_raw
    monkeypatch.setattr(Airtable, 'validate_session', rettrue)
    monkeypatch.setattr(Airtable, 'get_all', get_table_data)
    monkeypatch.setattr(requests, 'get', get_attach_patched)
    monkeypatch.setenv('AIRTABLE_API_KEY', '')
    table = download.DownloadTable(base_key='app12345', api_key='key12345',
                                   table_name='lots of fields')
    for item in table.download_table():
        assert item in lots_of_fields_correct
        filename = item['Attachments'][0]['filename']
        assert item['Attachments'][0]['md5hash'] ==\
            lots_of_fields_hashes[filename]
