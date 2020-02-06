import os
from datetime import timedelta
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    FLASK_APP = 'blog.py'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    ADMIN = 'sam0877@163.com'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEND_FILEMAX_AGE_DEFAULT = timedelta(seconds=1)
    POSTS_PER_PAGE = 15
    FOLLOWERS_PER_PAGE = 45
    COMMENTS_PER_PAGE = 30
    UPLOADED_PHOTOS_DEST = './app/static/uploads/'

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEGUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')

config = {
    'development': DevelopmentConfig,

    'default': DevelopmentConfig
}