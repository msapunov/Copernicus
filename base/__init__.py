from flask import Flask, g
from flask_login import current_user

from base.extensions import mail, cache, db, login_manager

from base.pages.login import bp as blueprint_login
from base.pages.project import bp as blueprint_project
from base.pages.user import bp as blueprint_user
from base.pages.board import bp as blueprint_board
from base.pages.admin import bp as blueprint_admin

from base.database.schema import User, Project

from datetime import datetime as dt
from werkzeug.exceptions import HTTPException
from os.path import join as path_join, exists

import logging
import logging.config


def create_app(config_filename):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile(config_filename)
    register_extensions(app)
    register_blueprints(app)
    register_decor(app)
    configure_logger(app)
    return app


def register_extensions(app):
    mail.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    return None


def register_blueprints(app):
    app.register_blueprint(blueprint_login)
    app.register_blueprint(blueprint_project)
    app.register_blueprint(blueprint_user)
    app.register_blueprint(blueprint_board)
    app.register_blueprint(blueprint_admin)
    return None


def register_decor(app):

    @app.template_filter("menu_item")
    def menu_item(obj):
        line = str(obj)
        line = line.replace("<TemplateReference '", "")
        line = line.replace(".html'>", "")
        return line

    @app.before_request
    def first_request():
        user_list = cache.get("user_list")
        if not user_list:
            users_obj = User.query.all()
            users = map(lambda x: x.login, users_obj)
            user_list = sorted(list(users))
            cache.set("user_list", user_list, 600)
        g.user_list = user_list

        if current_user.is_authenticated:
            g.permissions = current_user.permissions()
        else:
            g.permissions = []

        tmp = "%s" % dt.now()
        g.timestamp = tmp.split(".")[0]

        url_list = cache.get("url_list")
        if not url_list:
            url_list = ["%s" % rule for rule in app.url_map.iter_rules()]
            cache.set("url_list", url_list, 600)
        g.url_list = url_list

    @app.errorhandler(Exception)
    def handle_error(e):
        code = 500
        if isinstance(e, HTTPException):
            code = e.code
        logging.critical(str(e))
        return str(e), code

    return None


def configure_logger(app):
    cfg_file = app.config.get("LOG_CONFIG", "logging.cfg")
    cfg_path = path_join(app.instance_path, cfg_file)
    if exists(cfg_path):
        logging.config.fileConfig(cfg_path)
    else:
        print("No config found! Using default logger")
