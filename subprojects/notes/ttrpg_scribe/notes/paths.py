import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class Namespace:
    def __init__(self, id: str, root: Path):
        self.id = id
        self.root = root

    def get(self, subpath: str):
        return self.root/subpath

    def pages(self, subpath: str = '.'):
        return self.root/'pages'/subpath

    def assets(self, subpath: str = '.'):
        return self.root/'assets'/subpath

    def templates(self, subpath: str = '.'):
        return self.root/'templates'/subpath

    def build(self, subpath: str = '.'):
        return self.root/'_build'/subpath

    def built_assets(self, subpath: str = '.'):
        return self.build(f'assets/{subpath}')


__namespaces: dict[str, 'Namespace'] = {}
SETTING: Namespace | None
CAMPAIGN: Namespace


def for_namespace(namespace: str):
    return __namespaces[namespace]


def add_namespace(path: Path):
    name = path.resolve().name
    __namespaces[name] = Namespace(name, path)
    return __namespaces[name]


def init(project_dir_in: Path):
    global project_dir, namespaces, CAMPAIGN, SETTING
    project_dir = project_dir_in

    CAMPAIGN = add_namespace(project_dir)
    setting_dir = project_dir/'setting'
    if setting_dir.exists():
        SETTING = add_namespace(setting_dir)
    else:
        SETTING = None
    _LOGGER.info(f'Set project dir {project_dir}')


def __all(subpath: str = '.'):
    return (namespace.get(subpath) for namespace in __namespaces.values())


def all_pages():
    return __all('pages')


def all_templates():
    return __all('templates')
