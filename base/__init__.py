from flask import Flask, g, request
from flask_login import current_user

from base.extensions import mail, cache, db, login_manager

from base.pages.login import bp as blueprint_login
from base.pages.project import bp as blueprint_project
from base.pages.user import bp as blueprint_user
from base.pages.board import bp as blueprint_board
from base.pages.admin import bp as blueprint_admin
from base.pages.statistic import bp as blueprint_stat

from base.database.schema import User, Project

def create_app(config_filename: str) -> Flask:
    """Create and configure the Flask application instance.
    from base.functions import project_config, load_config
    Performs cleanup, registers extensions, blueprints, decorators, and
    logging, then attaches custom methods to the app object.

import logging
import logging.config
    Args:
        config_filename: Name of the configuration file located in the
            instance directory.


def create_app(config_filename):
    Returns:
        Configured Flask application instance.
    """
    cleanup()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile(config_filename)
    register_extensions(app)
    register_blueprints(app)
    register_decor(app)
    configure_logger(app)
    attach_custom_methods(app)
    if app.config.get("USE_GUNICORN", False):
        apply_proxy_fix(app)
    return app


def apply_proxy_fix(app: Flask) -> None:
    """Apply ProxyFix middleware for running behind a reverse proxy.

    Configures the Werkzeug ProxyFix to trust one proxy for the X-Forwarded-For,
    X-Forwarded-Proto, and X-Forwarded-Host headers.

    Args:
        app: Flask application instance.
    """
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=0  # 0 is for subpath deployments
    )


def register_extensions(app: Flask) -> None:
    """Initialize Flask extensions on the application instance.

    Registers Flask-Mail, Flask-Caching, Flask-SQLAlchemy, and Flask-Login.

    Args:
        app: Flask application instance.
    """
    mail.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register all page blueprints on the application instance.

    Registers login, project, user, board, admin, and statistic blueprints.

    Args:
        app: Flask application instance.
    """
    app.register_blueprint(blueprint_login)
    app.register_blueprint(blueprint_project)
    app.register_blueprint(blueprint_user)
    app.register_blueprint(blueprint_board)
    app.register_blueprint(blueprint_admin)
    app.register_blueprint(blueprint_stat)


def cleanup() -> bool:
    """Remove temporary directories from previous sessions.

    Scans the system temporary directory for directories whose names
    contain ``_copernicus_`` and removes them.

    Returns:
        True after cleanup is complete.
    """
    pattern = "_copernicus_"
    logging.debug("Temporary directory pattern: %s" % pattern)
    tmp_root = Path(gettempdir())
    logging.debug(f"Scanning {tmp_root} for temp dirs with prefix '{pattern}'")
    for entry in tmp_root.iterdir():
        if entry.is_dir() and pattern in entry.name:
            logging.debug(f"Cleanup from previous session: {entry}")
            try:
                rmtree(entry, ignore_errors=True)
            except Exception as e:
                logging.debug(f"Failed to remove {entry}: {e}")
    logging.info("Cleanup from previous session done")
    return True


def register_decor(app: Flask) -> None:
    """Register template filters, before-request handlers, and error handlers.

    Args:
        app: Flask application instance.
    """

    @app.template_filter("menu_item")
    def menu_item(obj: object) -> str:
        """Extract a menu-item name from a template reference.

        Args:
            obj: Template reference object.

        Returns:
            Cleaned template name without the enclosing HTML tags.
        """
        line = str(obj)
        line = line.replace("<TemplateReference '", "")
        line = line.replace(".html'>", "")
        return line

    @app.before_request
    def first_request() -> tuple | None:
        """Populate per-request globals: user list, config, permissions, URLs.

        Caches data for 10 minutes to reduce database and parsing overhead.
        Also blocks requests for JavaScript source maps.

        Returns:
            A 404 response for ``.js.map`` requests, or None to continue
            processing the request.
        """
        logging.debug("-" * 80)
        if request.path.endswith(".js.map"):
            return "", 404
        user_list = cache.get("user_list")
        if not user_list:
            users_obj = User.query.all()
            users = map(lambda x: x.login, users_obj)
            user_list = sorted(list(users))
            cache.set("user_list", user_list, 600)
        g.user_list = user_list

        config = cache.get("project_config")
        if not config:
            config_old = project_config()
            config = load_config()
            cache.set("project_config", config, 600)
        g.project_config = config

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
        return None

    @app.errorhandler(Exception)
    def handle_error(e: Exception) -> tuple[str, int]:
        """Log unhandled exceptions and return an error response.

        Args:
            e: The caught exception.

        Returns:
            A tuple of (error message string, HTTP status code).
        """
        if current_user.is_authenticated:
            user = current_user.full()
        else:
            user = "anonymous"
        url = request.url
        tb = format_exc()
        code = 500
        if isinstance(e, HTTPException):
            code = e.code
        if tb:
            logging.critical(tb + "User: %s\nRequest URL: %s" % (user, url))
        else:
            logging.critical(str(e))
        return str(e), code

    return None

    def get_tmpdir() -> str:
        """Get or create a temporary directory for the current date.

        The directory name includes today's date and the ``_copernicus_``
        prefix so it can be cleaned up on application restart.

        Returns:
            Absolute path to the temporary directory.
        """
        date_str = dt.now().strftime("%Y%m%d")
        prefix = f"{date_str}_copernicus_"
        temp_root = gettempdir()

        for root, dirs, _ in walk(temp_root):
            for d in dirs:
                if prefix in d:
                    dir_path = path_join(root, d)
                    logging.debug(f"Found directory: {dir_path}")
                    return dir_path
            break

        dir_path = mkdtemp(prefix=prefix)
        logging.debug(f"Directory created: {dir_path}")
        return dir_path
    setattr(app, "get_tmpdir", get_tmpdir)


def configure_logger(app: Flask) -> None:
    """Configure logging from a logging configuration file.

    Looks for the file specified by the ``LOG_CONFIG`` app config key
    inside the instance directory. Falls back to basic logging if the
    file is not found.

    Args:
        app: Flask application instance.
    """
    cfg_file = app.config.get("LOG_CONFIG", "logging.cfg")
    cfg_path = path_join(app.instance_path, cfg_file)
    if exists(cfg_path):
        logging.config.fileConfig(cfg_path)
    else:
        print("No config found! Using default logger")
