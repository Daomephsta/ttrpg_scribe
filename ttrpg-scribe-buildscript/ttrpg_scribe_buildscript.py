from pathlib import Path
import subprocess
from typing import MutableMapping

from pdm.backend.hooks import Context
from pdm.backend.hooks.version import scm


def pdm_build_hook_enabled(context: Context):
    return context.target == "sdist"


def pdm_build_initialize(context: Context):
    context.config.metadata['version'] = get_version(context)
    # Compile typescript
    build = context.ensure_build_dir()
    subprocess.call(['npx', 'tsc', '--outDir', build.as_posix()])


def pdm_build_update_files(context, files: MutableMapping[str, Path]):
    typescript_source = [f for f in files.keys() if f.endswith('.ts')]
    for file in typescript_source:
        del files[file]


def get_version(context: Context):
    version = scm.get_version_from_scm(context.root)
    assert version is not None
    [timestamp, commit] = subprocess.check_output(
        ['git', 'log', '-1', r'--format=%at %h'], text=True)\
        .strip().split(' ')
    dirty: str = '.dirty' if version.dirty else ''
    return f'{timestamp}+{version.branch}.git{commit}{dirty}'
