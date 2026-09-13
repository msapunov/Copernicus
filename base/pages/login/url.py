"""URL routes for the login blueprint: authentication, password reset,
and simple messaging.
"""

from base64 import b64decode
from logging import debug, error

from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from base.classes import Mail
from base.database.schema import User
from base.extensions import login_manager
from base.pages.login import bp
from base.pages.login.form import LoginForm, MessageForm, ResetForm
from base.pages.login.magic import password_errors, ssh_login

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


login_manager.login_view = "login.login"
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(uid):
    """Load a user from the database by ID (Flask-Login callback).

    Args:
        uid: User ID as stored in the session.

    Returns:
        User instance or None.
    """
    return User.query.filter_by(id=uid).first()


@bp.route("/api/<path:urlpath>", methods=["POST"])
def load_user_from_request(urlpath):
    """Authenticate a user via HTTP Basic Auth and redirect to the requested path.

    Expects an ``Authorization`` header with a Base64-encoded
    ``username:password`` pair.

    Args:
        urlpath: The path to redirect to after authentication.

    Returns:
        Redirect to the target path or to the login page.
    """
    api_key = request.headers.get("Authorization")
    if api_key:
        api_key = api_key.replace("Basic ", "", 1)
        try:
            api_key = b64decode(api_key)
        except TypeError:
            pass
        username, password = api_key.decode(encoding="UTF-8").split(":")
        if len(username) > 128:
            error("Username is longer then 128 letters")
            return abort(401)
        if not username.isalnum():
            error("Username '%s' consists not only from letters" % username)
            return abort(401)
        user = User.query.filter_by(login=username).first()
        debug("API user found %s" % user.login)
        if not user.check_password(password):
            return abort(401)
        login_user(user, True)
        if request.environ.get("SCRIPT_NAME"):
            urlpath = "%s/%s" % (request.environ["SCRIPT_NAME"], urlpath)
        else:
            urlpath = "/%s" % urlpath
        return redirect(urlpath, code=307)
    flash("API key is required")
    return redirect(url_for("login.login"))


@bp.route("/reset", methods=["GET", "POST"])
@bp.route("/reset.html", methods=["GET", "POST"])
@login_required
def reset():
    """Handle password reset requests.

    Validates the old password, checks new password strength and
    confirmation match, then updates the password.

    Returns:
        Rendered reset page or redirect.
    """
    form = ResetForm(request.form)
    if request.method == "GET":
        return render_template("reset.html", form=form)
    form.validate_on_submit()
    old = form.old.data
    new = form.new_passw.data
    conf = form.conf_passw.data
    if not current_user.check_password(old):
        flash("Old password is not correct!")
        return redirect(url_for("login.reset"))
    if new != conf:
        flash("New password does not match!")
        return redirect(url_for("login.reset"))
    if old == new:
        flash("New password match with old one!")
        return redirect(url_for("login.reset"))
    errors = password_errors(new)
    if errors:
        flash(errors)
        return redirect(url_for("login.reset"))
    current_user.set_password(new)
    flash("You have successfully changed your password!")
    return redirect(url_for("user.user_index"))


@bp.route("/login", methods=["GET", "POST"])
@bp.route("/login.html", methods=["GET", "POST"])
def login():
    """Handle user login via password or SSH authentication.

    Supports both database-hashed passwords and SSH key authentication
    against remote login servers.

    Returns:
        Rendered login page or redirect.
    """
    if current_user.is_authenticated:
        return redirect(url_for("user.user_index"))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html", form=form)

    form.validate_on_submit()
    username = form.login.data
    password = form.passw.data
    if not username or not password:
        flash("Username and password are required!")
        return redirect(url_for("login.login"))
    if len(username) > 128:
        flash("Username not correct")
        return redirect(url_for("login.login"))
    if not username.isalnum():
        flash("Username is not real")
        return redirect(url_for("login.login"))
    user = User.query.filter_by(login=username, active=True).first()
    if not user:
        flash("User '%s' does not exists" % username)
        return redirect(url_for("login.login"))
    else:
        debug(user.full())
        debug("Is user active: %s" % user.active)
        debug("Is user archived: %s" % user.archived)
    if not user.active:
        flash("User '%s' is deactivated" % username)
        return redirect(url_for("login.login"))
    if user.hash:
        debug("Using password verification")
        check = user.check_password(password)
    else:
        debug("Using SSH verification")
        check = ssh_login(username, password)
    if not check:
        flash("Invalid password")
        return redirect(url_for("login.login"))
    status = login_user(user, True)
    debug("Logged-in? %s" % status)
    g.name = username
    if user.first_login:
        return redirect(url_for("login.reset"))
    return redirect(url_for("user.user_index"))


@bp.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to the login page."""
    logout_user()
    return redirect(url_for("login.login"))


@bp.route("/message", methods=["POST"])
@login_required
def message():
    """Send a simple message via email.

    Expects JSON with ``destination``, ``title``, and ``body`` fields.

    Returns:
        JSON response confirming the message was sent.
    """
    form = MessageForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    msg = {
        "destination": form.destination.data,
        "title": form.title.data,
        "body": form.message.data,
    }
    Mail().simple_message(msg)
    return jsonify(data="Message sent")