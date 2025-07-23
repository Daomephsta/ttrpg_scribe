import os
import subprocess
import types
from functools import cached_property
from http import HTTPStatus
from pathlib import Path

import flask
import frontmatter
from jinja2 import FileSystemLoader, TemplateNotFound
from markupsafe import Markup
from werkzeug.exceptions import NotFound

import ttrpg_scribe.core.flask
import ttrpg_scribe.dnd_bestiary.apis
import ttrpg_scribe.dnd_bestiary.flask
from ttrpg_scribe.core import markdown, script_loader
from ttrpg_scribe.notes import (content_tree, data_script, paths,
                                run_script_shim)


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

        def exec_pyfile(path: Path, locals):
            module = types.ModuleType('config')
            module.__file__ = path.as_posix()
            with path.open('rb') as file:
                exec(compile(file.read(), path, 'exec'),
                     module.__dict__, locals)

        config_obj = {}
        setting_config = project_dir/'setting/config.py'
        if setting_config.exists():
            exec_pyfile(setting_config, config_obj)
        exec_pyfile(config, config_obj)
        self.config.from_mapping(config_obj)
        if 'TOOLS' not in self.config:
            self.config['TOOLS'] = []

    @cached_property
    def jinja_loader(self) -> FileSystemLoader | None:  # type: ignore
        super_loader = super().jinja_loader
        assert super_loader
        return FileSystemLoader([
            *super_loader.searchpath,
            *paths.all_pages(),
            *paths.all_templates()
        ])


def create_app(config: Path, project_dir: str | Path | None = None):
    app = Notes(Path(project_dir) if project_dir else Path.cwd(), config)
    tools: list[tuple[str, str, dict]] = app.config['TOOLS']
    tools.append(('/clean', 'Clean _build', {'method': 'post'}))
    ttrpg_scribe.core.flask.extend(app)

    @app.get('/')
    @app.get('/index/')
    @app.get('/index/<path:subtree>')
    def index(subtree: str = ''):
        return flask.render_template('index.j2.html',
            content_tree=content_tree.walk(f'pages/{subtree}'),
            subtree=Path(subtree))

    @app.get('/notes/<namespace_id>/<path:page>.html')
    def serve_html(namespace_id: str, page: str):
        namespace = paths.for_namespace(namespace_id)
        if (namespace.pages(page).exists()):
            return flask.send_from_directory(namespace.pages(), page)
        templates = [f'{page}.j2.{ext}' for ext in ['html', 'md']]
        try:
            selected = app.jinja_env.select_template(templates)
            assert selected.name is not None
        except TemplateNotFound as e:
            tried = ', '.join(str(namespace.pages(template))
                              for template in templates)
            # Can be an error with other templates
            if e.templates == templates:
                return flask.abort(HTTPStatus.NOT_FOUND,
                    description=f"None of [{tried}] found")
            else:
                raise

        def dump(folder: str, extension: str):
            if os.getenv(f'ttrpg_scribe_DUMP_{extension.upper()}') == '1':
                dump = namespace.build(f'{folder}/{page}.{extension}')
                dump.parent.mkdir(parents=True, exist_ok=True)
                dump.write_text(rendered)

        rendered = flask.render_template(selected,
            script=data_script.bind(namespace, selected.name))
        if selected.name.endswith('.md'):
            dump('markdown', 'md')
            metadata, md = frontmatter.parse(rendered)
            metadata = markdown.parse_metadata(metadata)
            page_assets = flask.g.assets
            page_assets['stylesheets'] = page_assets['stylesheets'].union(
                metadata['extra_stylesheets'])
            page_assets['scripts'] += metadata['extra_scripts']
            html_fragment, toc = markdown.convert(md)
            return flask.render_template(f"layout/{metadata['layout']}.j2.html",
                                         content=Markup(html_fragment), toc=toc)
        return rendered

    @app.get('/assets/<namespace_id>/<path:asset>')
    def assets(namespace_id: str, asset: str):
        namespace = paths.for_namespace(namespace_id)
        try:
            return flask.send_from_directory(namespace.assets(), asset)
        except NotFound:
            raise NotFound(f'{asset} not found in {namespace.assets()}')

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
