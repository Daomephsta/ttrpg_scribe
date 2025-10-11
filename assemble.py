#!/usr/bin/env python
import subprocess
from pathlib import Path
import shutil
import zipfile
import ttrpg_scribe_buildscript

root = Path.cwd()
subprojects = list((root/'subprojects').iterdir())
dest = root/'dist/assemble'


def clean():
    print('Cleaning')
    try:
        subprocess.run(['pdm', 'cache', 'remove', 'ttrpg_scribe_buildscript*'], check=True)
    except subprocess.CalledProcessError as e:
        if e.returncode != 1:
            raise e from None
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for path in (root/'dist').glob('ttrpg_scribe-*.zip'):
        path.unlink()


def setup_build_dependencies():
    subprocess.run(['npm', 'ci'], check=True)
    # Install plugins sequentially to avoid contention over ttrpg-scribe-buildscript/.pdm-build
    for project in subprojects:
        if (plugins := project/'.pdm-plugin').exists():
            shutil.rmtree(plugins)
        subprocess.run(
            ['pdm', 'install', '--plugins'],
            cwd=project, check=True
        )


class BuildTask:
    def __init__(self, project: Path) -> None:
        self.project = project
        self._process = subprocess.Popen(
            ['pdm', 'build', '--no-clean', '-d', dest],
            cwd=project
        )

    def is_running(self):
        match self._process.poll():
            case None:
                return True
            case 0:
                return False
            case err:
                e = subprocess.CalledProcessError(err, self._process.args)
                e.add_note(f'project={self.project.as_posix()}')
                raise e

    def terminate(self):
        self._process.terminate()


def build_wheels():
    print('Building wheels')
    build_tasks = [BuildTask(project) for project in subprojects]

    while len(build_tasks) > 0:
        try:
            build_tasks = [task for task in build_tasks if task.is_running()]
        except subprocess.CalledProcessError as e:
            for task in build_tasks:
                task.terminate()
            raise e from None


def assemble():
    version = ttrpg_scribe_buildscript.get_version(root)
    with zipfile.ZipFile(root/f'dist/ttrpg_scribe-{version}.zip', 'w') as zip:
        print(f'Assembling {zip.filename}')
        for wheel in dest.glob('*.whl'):
            zip.write(wheel, wheel.name)


clean()
setup_build_dependencies()
build_wheels()
assemble()
