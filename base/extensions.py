# -*- coding: utf-8 -*-
"""
Extensions module. Each extension is initialized in the app factory located in
__init__.py
"""

from flask_caching import Cache
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

mail = Mail()
"""Flask-Mail extension instance for sending emails."""

login_manager = LoginManager()
"""Flask-Login extension instance for user session management."""

db = SQLAlchemy()
"""Flask-SQLAlchemy extension instance for database access."""

cache = Cache()
"""Flask-Caching extension instance for caching data."""
