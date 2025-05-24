from dataclasses import dataclass
from enum import Enum, auto
from functools import reduce
from pathlib import Path
import re
import sys

from ttrpg_scribe.core import markdown
from ttrpg_scribe.notes import paths
import yaml


@dataclass
class Content:
    url: str
    title: str

    class Type(Enum):
        Directory = auto()
        File = auto()
    type: Type
    children: dict[str, 'Content']

    def __init__(self, namespace: paths.Namespace, absolute_path: Path, title: str) -> None:
        def find_url():
            url = absolute_path.relative_to(namespace.pages())
            if self.is_file():
                url = namespace.id/url
            match url.suffixes:
                case ['.j2', '.md'] | ['.j2', '.html'] as suffixes:
                    name = reduce(str.removesuffix, suffixes, url.name)
                    url = url.with_name(name).with_suffix('.html')
            return url.as_posix()

        self.namespace = namespace
        self.type = Content.Type.File if absolute_path.is_file()\
            else Content.Type.Directory
        self.url = find_url()
        self.title = title
        self.children = {}

    def __find_title(self, path: Path) -> str:
        if path.suffixes == ['.j2', '.md']:
            with open(path, encoding='utf-8') as file:
                title = markdown.find_title(file.read())
                if title:
                    return title
        title = reduce(str.removesuffix, path.suffixes, path.name)
        title = re.sub('[_-]', ' ', title)
        return title

    def add_child(self, path: Path) -> 'Content':
        child = Content(self.namespace, path, self.__find_title(path))
        self.children[path.name] = child
        return child

    def is_file(self) -> bool:
        return self.type == Content.Type.File

    def __iter__(self):
        return iter(self.children.items())


def walk(path: str) -> Content:
    def transform_index(index: dict | list) -> dict:
        match index:
            case dict():
                return {k: transform_index(v) for k, v in index.items()}
            case list():
                transformed = {}
                for i, e in enumerate(index):
                    match e:
                        case dict():
                            k, v = next(iter(e.items()))
                            transformed[k] = i, transform_index(v)
                        case _:
                            transformed[e] = i
                return transformed

    def load_index(dir: Path) -> dict:
        if (dir/'index.yml').exists():
            with (dir/'index.yml').open() as file:
                return transform_index(yaml.safe_load(file))
        return {}

    def get_subindex(root_index: dict, root: Path, subpath: Path):
        relative = subpath.relative_to(root)
        subindex: dict | tuple[int, dict] = root_index
        for part in relative.parts:
            match subindex:
                case dict():
                    subindex = subindex.get(part, {})
                case _, dict() as children:
                    subindex = children.get(part, {})
        return subindex

    def walk_subtree(dir: Path, subtree: Content, index: dict | tuple[int, dict]):
        if not dir.exists():
            return subtree

        if isinstance(index, tuple):
            _, index = index

        def by_index(path: Path):
            match index.get(path.name):
                case (int() as ordinal, dict()):
                    ordinal = ordinal
                case int() as ordinal:
                    ordinal = ordinal
                case None:
                    ordinal = sys.maxsize
                case unknown:
                    raise ValueError(unknown)
            return ordinal, path.name

        for path in sorted(dir.iterdir(), key=by_index):
            if path.name in ['assets', '__pycache__', 'index.yml'] or path.suffix == '.py':
                continue
            child = subtree.add_child(path)
            if path.is_dir():
                walk_subtree(path, child, index.get(path.stem, {}))
        return subtree

    campaign_path = paths.CAMPAIGN.get(path)
    campaign_index = load_index(paths.CAMPAIGN.pages())
    root = walk_subtree(
        campaign_path, Content(paths.CAMPAIGN, campaign_path, ''),
        get_subindex(campaign_index, paths.CAMPAIGN.pages(), campaign_path))
    if paths.SETTING is not None:
        setting_index = load_index(paths.CAMPAIGN.pages())
        setting_path = paths.SETTING.get(path)
        root.children['setting'] = walk_subtree(
            setting_path, Content(paths.SETTING, setting_path, 'setting'),
            get_subindex(setting_index, paths.SETTING.pages(), setting_path))
    return root
