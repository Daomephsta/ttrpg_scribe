import os
from functools import cached_property
from http import HTTPStatus
from pathlib import Path

import flask
from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound

import dnd_scribe.core.flask
from dnd_scribe.core import markdown
from dnd_scribe.notes import data_cache, data_script, paths


class Notes(flask.Flask):
    def __init__(self, project_dir: Path):
        super().__init__('dnd_scribe.notes')
        self.jinja_options.update(
            trim_blocks = True,
            lstrip_blocks = True)
        paths.initialise(self, project_dir)

    @cached_property
    def jinja_loader(self) -> ChoiceLoader:
        super_loader = super().jinja_loader
        assert super_loader
        return ChoiceLoader([
            super_loader,
            FileSystemLoader([
                paths.current().pages,
                paths.current().templates
            ])
        ])

def create_app(project_dir: str | Path | None = None):
    app = Notes(Path(project_dir) if project_dir else Path.cwd())
    app.register_blueprint(dnd_scribe.core.flask.blueprint)
    data_cache.initialise(app)

    @app.get('/notes/<path:page>.html')
    def serve_html(page: str):
        if (paths.current().pages/page).exists():
            return flask.send_from_directory(paths.current().pages, page)
        templates = [f'{page}.j2.{ext}' for ext in ['html', 'md']]
        try:
            selected = app.jinja_env.select_template(templates)
            assert selected.name is not None
        except TemplateNotFound as e:
            tried = ', '.join(str(paths.current().pages/template)
                                      for template in templates)
            # Can be an error with other templates
            if e.templates == templates:
                return flask.abort(HTTPStatus.NOT_FOUND,
                    description=f"None of [{tried}] found")
            else:
                raise
        rendered = flask.render_template(selected,
            script=data_script.bind(selected.name))
        if selected.name.endswith('.md'):
            if os.getenv('DND_SCRIBE_DUMP_MD') == '1':
                raise NotImplementedError
            return markdown.render(rendered)
        return rendered

    return app