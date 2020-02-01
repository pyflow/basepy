
from basepy.config import Settings
from box import Box
import os

def test_config_1():
    st = Settings()
    st._store = Box({'hello': "world", 'foo':1}, box_it_up=True, frozen_box=True)
    assert st.hello == "world"
    assert st.foo == 1
    st._secrets = Box({'key1': "value1", 'key2': 23}, box_it_up=True, frozen_box=True)
    assert st.secrets.key1 == "value1"
    assert st.secrets.key2 == 23


def test_config_load(request):
    fspath = request.node.fspath
    fsdir = os.path.dirname(fspath)
    st = Settings(root_path=os.path.join(fsdir, 'assets/config_1'))
    assert len(st.log.handlers) == 2
    assert st.secrets.signing_secret == 'a'
    assert st.secrets.access_token == 'b'

def test_config_load_local(request):
    fspath = request.node.fspath
    fsdir = os.path.dirname(fspath)
    st = Settings(root_path=os.path.join(fsdir, 'assets/config_2'))
    assert len(st.log.handlers) == 1
    assert st.secrets.signing_secret == 'local_a'
    assert st.secrets.access_token == 'local_b'