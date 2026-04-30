from flask import Flask

from app.config import Config
from app.database import init_app
from app.routes import main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable Jinja2 extensions
    app.jinja_env.add_extension('jinja2.ext.do')

    init_app(app)
    app.register_blueprint(main_bp)

    return app
