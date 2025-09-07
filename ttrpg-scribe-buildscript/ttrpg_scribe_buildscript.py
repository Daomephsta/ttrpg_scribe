import subprocess

from pdm.backend.hooks import Context
from pdm.backend.hooks.version import scm


def pdm_build_hook_enabled(context: Context):
    return context.target == "sdist"


def pdm_build_initialize(context: Context):
    context.config.metadata['version'] = get_version(context)
    # Compile typescript
    build = context.ensure_build_dir()
    subprocess.call(['npx', 'tsc', '--outDir', build.as_posix()])


def get_version(context: Context):
    version = scm.get_version_from_scm(context.root)
    assert version is not None
    [timestamp, commit] = subprocess.check_output(
        ['git', 'log', '-1', r'--format=%at %h'], text=True)\
        .strip().split(' ')
    dirty: str = '.dirty' if version.dirty else ''
    return f'{timestamp}+{version.branch}.git{commit}{dirty}'
