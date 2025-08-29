import subprocess

from pdm.backend.hooks import Context
from pdm.backend.hooks.version import SCMVersion


def format_version(version: SCMVersion):
    [timestamp, commit] = subprocess.check_output(
        ['git', 'log', '-1', r'--format=%at %h'], text=True)\
        .strip().split(' ')
    dirty: str = '.dirty' if version.dirty else ''
    return f'{timestamp}+{version.branch}.git{commit}{dirty}'


def pdm_build_initialize(context: Context):
    if context.target != "sdist":
        return
    build = context.ensure_build_dir()
    subprocess.call(['npx', 'tsc', '--outDir', build.as_posix()])
