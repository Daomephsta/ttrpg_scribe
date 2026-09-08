#!/usr/bin/env python
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

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
    subprocess.run(['pdm', 'build'],
        cwd=root/'ttrpg-scribe-buildscript', check=True)
    # Install plugins sequentially to avoid contention over ttrpg-scribe-buildscript/.pdm-build
    for project in subprojects:
        if (plugins := project/'.pdm-plugin').exists():
            shutil.rmtree(plugins)
        subprocess.run(
            ['pdm', 'install', '--plugins'],
            cwd=project, check=True
        )



def build_wheels():
    print('Building wheels')
    build_tasks: list[tuple[subprocess.Popen[bytes], dict[str, Any]]] = [(
            subprocess.Popen(
            ['pdm', 'build', '--no-clean', '-d', dest, *(['-v'] if '-v' in sys.argv else [])],
            cwd=project
            ),
            {'cwd': project}
        )
        for project in subprojects
    ]

    def is_running(task: subprocess.Popen[bytes], task_info: dict[str, Any]):
        match task.poll():
            case None:
                return True
            case 0:
                return False
            case err:
                e = subprocess.CalledProcessError(err, task.args)
                for k, v in task_info.items():
                    e.add_note(f'{k}={v}')
                raise e

    while len(build_tasks) > 0:
        try:
            build_tasks = [task for task in build_tasks if is_running(*task)]
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            for task, _ in build_tasks:
                task.terminate()
            raise e from None


def assemble():
    version = next(dest.glob('ttrpg_scribe_core-*.whl')).stem.removeprefix('ttrpg_scribe_core-')
    with zipfile.ZipFile(root/f'dist/ttrpg_scribe-{version}.zip', 'w') as zip:
        print(f'Assembling {zip.filename}')
        for wheel in dest.glob('*.whl'):
            zip.write(wheel, wheel.name)


clean()
setup_build_dependencies()
build_wheels()
assemble()
