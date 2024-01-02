import os
from functools import cached_property
from http import HTTPStatus
from pathlib import Path

import flask
from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound
from werkzeug.exceptions import NotFound

import dnd_scribe.bestiary.apis
import dnd_scribe.bestiary.flask
import dnd_scribe.core.flask
from dnd_scribe.core import markdown
from dnd_scribe.notes import content_tree, data_script, paths


class Notes(flask.Flask):
    def __init__(self, project_dir: Path):
        super().__init__('dnd_scribe.notes',
            instance_path=project_dir.absolute().as_posix(),
            instance_relative_config=True)
        self.jinja_options.update(
            trim_blocks=True,
            lstrip_blocks=True)
        self.config.from_pyfile('config.py')

    @cached_property
    def jinja_loader(self) -> ChoiceLoader:
        super_loader = super().jinja_loader
        assert super_loader
        return ChoiceLoader([
            super_loader,
            FileSystemLoader([paths.pages(), paths.templates()])
        ])


def create_app(project_dir: str | Path | None = None):
    app = Notes(Path(project_dir) if project_dir else Path.cwd())
    dnd_scribe.core.flask.extend(app)

    @app.get('/')
    @app.get('/index.html')
    def index():
        return flask.render_template('index.j2.html',
    content_tree=content_tree.walk())

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
            if os.getenv(f'DND_SCRIBE_DUMP_{extension.upper()}') == '1':
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

    return app
