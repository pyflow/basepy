
import yaml
from basepy.config import Settings


def load_yaml(content_str):
    ret = yaml.safe_load(content_str)
    return ret

def load():
    Settings.register_loader('.yaml', load_yaml)
    Settings.register_loader('.yml', load_yaml)