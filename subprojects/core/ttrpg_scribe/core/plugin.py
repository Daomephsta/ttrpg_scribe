from pathlib import Path

from flask import Config, Flask


class Plugin:
    @classmethod
    def create_app(cls, instance_path: Path, config: Config) -> Flask:
        ...

    @classmethod
    def configure(cls, main_app: Flask):
        ...
