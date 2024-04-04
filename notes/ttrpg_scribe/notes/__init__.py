import os
from functools import cached_property
from http import HTTPStatus
from pathlib import Path
import subprocess

import flask
from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound
from markupsafe import Markup
from werkzeug.exceptions import NotFound

import ttrpg_scribe.core.flask
import ttrpg_scribe.dnd_bestiary.apis
import ttrpg_scribe.dnd_bestiary.flask
from ttrpg_scribe.core import markdown, script_loader
from ttrpg_scribe.notes import content_tree, data_script, paths, run_script_shim


class Notes(flask.Flask):
    def __init__(self, project_dir: Path, config: Path):
        super().__init__('ttrpg_scribe.notes',
            instance_path=project_dir.absolute().as_posix(),
            instance_relative_config=True)
        self.jinja_options.update(
            trim_blocks=True,
            lstrip_blocks=True)
        paths.init(Path(self.instance_path))
        script_loader.add_library_folder('scripts')
        self.config.from_pyfile(config)

    @cached_property
    def jinja_loader(self) -> ChoiceLoader:
        super_loader = super().jinja_loader
        assert super_loader
        return ChoiceLoader([
            super_loader,
            FileSystemLoader([paths.pages(), paths.templates()])
        ])


def create_app(config: Path, project_dir: str | Path | None = None):
    app = Notes(Path(project_dir) if project_dir else Path.cwd(), config)
    ttrpg_scribe.core.flask.extend(app)

    @app.get('/')
    @app.get('/index/')
    @app.get('/index/<path:subtree>')
    def index(subtree: str = ''):
        return flask.render_template('index.j2.html',
            content_tree=content_tree.walk(paths.pages()/subtree), subtree=Path(subtree))

    @app.get('/notes/<path:page>.html')
    def serve_html(page: str):
        if (paths.pages()/page).exists():
            return flask.send_from_directory(paths.pages(), page)
        templates = [f'{page}.j2.{ext}' for ext in ['html', 'md']]
        try:
            selected = app.jinja_env.select_template(templates)
            assert selected.name is not None
        except TemplateNotFound as e:
            tried = ', '.join(str(paths.pages()/template)
                              for template in templates)
            # Can be an error with other templates
            if e.templates == templates:
                return flask.abort(HTTPStatus.NOT_FOUND,
                    description=f"None of [{tried}] found")
            else:
                raise

        def dump(folder: str, extension: str):
            if os.getenv(f'ttrpg_scribe_DUMP_{extension.upper()}') == '1':
                dump = paths.build()/f'{folder}/{page}.{extension}'
                dump.parent.mkdir(parents=True, exist_ok=True)
                dump.write_text(rendered)

        rendered = flask.render_template(selected,
            script=data_script.bind(selected.name))
        if selected.name.endswith('.md'):
            dump('markdown', 'md')
            rendered = markdown.render(rendered)
        return rendered

    @app.get('/assets/<path:asset>')
    def assets(asset: str):
        try:
            return flask.send_from_directory(paths.assets(), asset)
        except NotFound:
            raise NotFound(f'{asset} not found in {paths.assets()}')

    @app.get('/scripts')
    def list_scripts():
        scripts_folder = paths.project_dir/'scripts'

        def scripts():
            for path in scripts_folder.glob('*.py'):
                if path.name.startswith('__'):
                    continue
                yield path, Markup(path.with_suffix('.html').read_text('utf8'))
        return flask.render_template('script_list.j2.html', scripts=scripts())

    @app.post('/scripts/run')
    def run_script():
        script = flask.request.form['script']
        args = [f'{k}={v}' for k, v in flask.request.form.items() if k != 'script']
        script_file = paths.project_dir/'scripts'/script
        script_result = subprocess.run(
            ['python', run_script_shim.__file__, script_file.as_posix(), *args],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8')
        return script_result.stdout, {'Content-Type': 'text/plain'}

    return app
