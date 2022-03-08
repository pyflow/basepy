import pytest
from basepy.more import yaml_config
from basepy.config import settings, Settings
from box import Box
import os

yaml_config.load()


def test_yaml_loaded():
    assert '.yaml' in Settings._ext_list
    assert '.yaml' in Settings._ext_loaders
    assert '.yml' in Settings._ext_list
    assert '.yml' in Settings._ext_loaders

@pytest.fixture
def asset_dir(request):
    return os.path.join(request.config.rootdir, 'tests', 'assets')

def test_config_1():
    st = Settings()
    st._store = Box({'hello': "world", 'foo':1}, box_it_up=True, frozen_box=True)
    assert st.hello == "world"
    assert st.foo == 1
    st._secrets = Box({'key1': "value1", 'key2': 23}, box_it_up=True, frozen_box=True)
    assert st.secrets.key1 == "value1"
    assert st.secrets.key2 == 23


def test_config_load(asset_dir):
    st = Settings(root_path=os.path.join(asset_dir, 'config_1'))
    assert len(st.log.handlers) == 2
    assert st.secrets.signing_secret == 'a'
    assert st.secrets.access_token == 'b'

def test_config_load_local(asset_dir):
    st = Settings(root_path=os.path.join(asset_dir, 'config_2'))
    assert len(st.log.handlers) == 1
    assert st.secrets.signing_secret == 'local_a'
    assert st.secrets.access_token == 'local_b'


def test_config_load_yaml(asset_dir):
    st = Settings(root_path=os.path.join(asset_dir, 'yamlconfig_1'))
    assert len(st.log.handlers) == 2
    assert st.secrets.signing_secret == 'a'
    assert st.secrets.access_token == 'b'