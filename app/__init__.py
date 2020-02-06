#-*-coding:utf-8-*-
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_moment import Moment
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config
import os
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class

bootstrap = Bootstrap()
db = SQLAlchemy()
moment = Moment()
login_manager = LoginManager()
login_manager.login_view = '.login'
pagedown = PageDown()
photos = UploadSet('photos', IMAGES)

def create_app(config_name):
    os.environ['FLASK_APP'] = 'blog.py'
    app = Flask(__name__)
    os.environ['FLASK_APP'] = 'blog.py'
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)
    configure_uploads(app, photos)
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app