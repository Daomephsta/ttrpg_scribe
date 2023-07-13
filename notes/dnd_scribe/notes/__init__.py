import os
from functools import cached_property
from http import HTTPStatus
from pathlib import Path

import flask
from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound

import dnd_scribe.core.flask
from dnd_scribe.core import markdown


class Notes(flask.Flask):
    def __init__(self, project_folder: Path):
        super().__init__('dnd_scribe.notes')
        self.project_folder = project_folder
        self.config[f'{self.import_name}_project_folder'] = project_folder
        self.jinja_options.update(
            trim_blocks = True,
            lstrip_blocks = True)

    @cached_property
    def jinja_loader(self) -> ChoiceLoader:
        super_loader = super().jinja_loader
        assert super_loader
        return ChoiceLoader([
            super_loader,
            FileSystemLoader([self.project_folder])
        ])

def create_app(project_folder: str | Path | None = None):
    app = Notes(Path(project_folder) if project_folder else Path.cwd())
    app.register_blueprint(dnd_scribe.core.flask.blueprint)

    @app.get('/notes/<path:page>.html')
    def serve_html(page: str):
        if (app.project_folder/page).exists():
            return flask.send_from_directory(app.project_folder, page)
        templates = [f'{page}.j2.{ext}' for ext in ['html', 'md']]
        try:
            selected = app.jinja_env.select_template(templates)
            assert selected.name is not None
            rendered = flask.render_template(selected)
            if selected.name.endswith('.md'):
                if os.getenv('DND_SCRIBE_DUMP_MD') == '1':
                    raise NotImplementedError
                return markdown.render(rendered)
            return rendered
        except TemplateNotFound as e:
            tried = ', '.join(str(app.project_folder/template)
                                      for template in templates)
            if e.templates == templates:
                return flask.abort(HTTPStatus.NOT_FOUND,
                    description=f"None of [{tried}] found")
            else:
                raise

    return app