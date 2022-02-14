
import os
import toml
from box import Box
import json

class Missing:
    """
    Sentinel value object/singleton used to differentiate between ambiguous
    situations where `None` is a valid value.
    """

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__)

    def __repr__(self) -> str:
        return "<Missing>"


missing = Missing()

class Settings(object):

    __slots__ = ['_fresh', '_store', "_secrets", '_defaults', 'root_path']

    def __init__(self, root_path=None, **kwargs):
        self._fresh = False
        self._store = Box(data={}, box_it_up=True, frozen_box=True)
        self._secrets = Box(data={}, box_it_up=True, frozen_box=True)
        self._defaults = kwargs
        self._config_files = []
        self._secrets_files = []
        self._ext_list = ['.toml', '.json']
        self._ext_loaders = {}
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
    
    def register_loader(self, ext, loader_func):
        if not callable(loader_func):
            raise Exception('loader_func must be callable, and accept text content as parameter.')
        if not ext.startswith('.'):
            raise Exception('ext must be start with ".", for example, using ".json" instead of "json"')
        self._ext_loaders[ext] = loader_func
        if ext not in self._ext_list:
            self._ext_list.append(ext)

    def as_dict(self, env=None, internal=False):
        data = self.store.to_dict().copy()
        return data

    to_dict = as_dict

    def get(self, key, default=None):
        data = self.store.get(key, default)
        return data

    def exists(self, key):
        return self.get(key,default=missing) is not missing

    def reload(self, env=None, silent=None):  # pragma: no cover
        self.execute_loaders(env, silent)

    def execute_loaders(self, env=None, silent=None):
        config_files = []
        secrets_files = []
        
        def check_setting_files(root, configs):
            for prefix in ["settings", "settings.local"]:
                for name in map(lambda x: "{}{}".format(prefix, x), self._ext_list):
                    fpath = os.path.join(root, name)
                    if os.path.exists(fpath) and os.path.isfile(fpath):
                        configs.append(fpath)
                        continue

        def check_secrets_files(root, secrets):
            for prefix in [".secrets", ".secrets.local"]:
                for name in map(lambda x: "{}{}".format(prefix, x), self._ext_list):
                    fpath = os.path.join(root, name)
                    if os.path.exists(fpath) and os.path.isfile(fpath):
                        secrets.append(fpath)
                        continue

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
        self._config_files = config_files

        secrets = map(lambda x: self.load_file(x), secrets_files)
        secrets_data = {}
        for data in secrets:
            secrets_data.update(data)

        self._secrets = Box(secrets_data, box_it_up=True, frozen_box=True)
        self._secrets_files = secrets_files


    def load_file(self, path=None, env=None, silent=True):
        root, ext = os.path.splitext(path)
        if ext == '.toml':
            return self.load_toml(path)
        elif ext == '.json':
            return self.load_json(path)

    def load_toml(self, path):
        return toml.load(path)

    def load_with_extloader(self, path, ext):
        with open(path, 'rb') as f:
            ext_loader = self.ext_loaders[ext]
            return ext_loader(f.read())

    def load_json(self, path):
        with open(path, 'rb') as f:
            return json.loads(f.read())

settings = Settings()