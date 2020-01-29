import glob
import importlib
import os
import toml
import yaml
from box import Box

class Settings(object):
    
    __slots__ = ['_fresh', '_store', "_secrets", '_defaults', 'root_path']

    def __init__(self, root_path=None, **kwargs):
        self._fresh = False
        self._store = Box(data={}, box_it_up=True, frozen_box=True)
        self._secrets = Box(data={}, box_it_up=True, frozen_box=True)
        self._defaults = kwargs
        self.root_path = root_path or os.getcwd() 
        self.execute_loaders()

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def __getattr__(self, name):
        value = self.get(name)
        if value is None:
            raise KeyError("{0} does not exists".format(name))
        return value

    def __delattr__(self, name):
        raise Exception('Deleting attr not allowed.')

    def __contains__(self, item):
        return item in self.store

    def __getitem__(self, item):
        value = self.get(item)
        if value is None:
            raise KeyError("{0} does not exists".format(item))
        return value

    @property
    def store(self):
        return self._store
    
    @property
    def secrets(self):
        return self._secrets

    def keys(self):
        return self.store.keys()

    def values(self):
        return self.store.values()

    def as_dict(self, env=None, internal=False):
        data = self.store.to_dict().copy()
        return data

    to_dict = as_dict

    def get(self, key, default=None):
        data = self.store.get(key, default)
        return data

    def exists(self, key):
        return self.get(key, fresh=fresh, default=missing) is not missing


    def as_bool(self, key):
        return self.get(key, cast="@bool")

    def as_int(self, key):
        return self.get(key, cast="@int")

    def as_float(self, key):
        return self.get(key, cast="@float")

    def as_json(self, key):
        return self.get(key, cast="@json")

    def reload(self, env=None, silent=None):  # pragma: no cover
        self.execute_loaders(env, silent)

    def execute_loaders(self, env=None, silent=None):
        config_files = []
        secrets_files = []
        def check_setting_files(root, configs):
            for name in ['settings.toml', 'settings.yaml', 'settings.local.toml', 'settings.local.yaml']:
                fpath = os.path.join(root, name)
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    configs.append(fpath)
        
        def check_secrets_files(root, secrets):
            for name in ['.secrets.toml', '.secrets.yaml', '.secrets.local.toml', '.secrets.local.yaml']:
                fpath = os.path.join(root, name)
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    secrets.append(fpath)

        root = self.root_path
        config_dir = os.path.join(root, "config")
        if os.path.isdir(config_dir):
            check_setting_files(config_dir, config_files)
            check_secrets_files(config_dir, secrets_files)

        if len(config_files) == 0:
            check_setting_files(root, config_files)
        
        if len(secrets_files) == 0:
            check_secrets_files(root, secrets_files)
        
        configs = map(lambda x: self.load_file(x), config_files)
        config_data = {}
        for data in configs:
            config_data.update(data)
        
        self._store = Box(config_data, box_it_up=True, frozen_box=True)

        secrets = map(lambda x: self.load_file(x), secrets_files)
        secrets_data = {}
        for data in secrets:
            secrets_data.update(data)
        
        self._secrets = Box(secrets_data, box_it_up=True, frozen_box=True)

        
    def load_file(self, path=None, env=None, silent=True):
        root, ext = os.path.splitext(path)
        if ext == '.toml':
            return self.load_toml(path)
        elif ext == '.yaml':
            return self.load_yaml(path)
    
    def load_toml(self, path):
        try:
            return toml.load(path)
        except:
            return {}

    def load_yaml(self, path):
        try:
            return yaml.load(path)
        except:
            return {}

settings = Settings()