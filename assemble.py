#!/usr/bin/env python
import subprocess
from pathlib import Path
import shutil
import zipfile


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


def build_wheels():
    print('Building wheels')
    build_tasks = [
        subprocess.Popen(
            ['pdm', 'build', '--no-clean', '-d', dest],
            cwd=project
        ) for project in subprojects
    ]

    def is_running(task: subprocess.Popen):
        match task.poll():
            case None:
                return True
            case 0:
                return False
            case err:
                raise subprocess.CalledProcessError(err, task.args)

    while len(build_tasks) > 0:
        try:
            build_tasks = [task for task in build_tasks if is_running(task)]
        except subprocess.CalledProcessError as e:
            for task in build_tasks:
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
