# -*- coding: utf-8 -*-
"""
Extensions module. Each extension is initialized in the app factory located in
__init__.py
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_mail import Mail


mail = Mail()
login_manager = LoginManager()
db = SQLAlchemy()
cache = Cache()
