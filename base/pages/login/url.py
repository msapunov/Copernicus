from flask import render_template, request, redirect, url_for, g, flash, abort
from flask_login import current_user, login_user, logout_user, login_required
from base.pages.login.magic import ssh_login, password_quality
from base.pages.login.form import LoginForm, ResetForm
from base.pages.login import bp
from base64 import b64decode
from base.database.schema import User
from base.extensions import login_manager


from logging import warning, debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


login_manager.login_view = "login.login"
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(userid):
    return User.query.filter(User.id == userid).first()


@bp.route("/api/<path:urlpath>", methods=["POST"])
def load_user_from_request(urlpath):
    api_key = request.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Basic ', '', 1)
        try:
            api_key = b64decode(api_key)
        except TypeError:
            pass
        username, password = api_key.decode(encoding="UTF-8").split(":")
        if not ssh_login(username, password):
            return abort(401)
        user = User.query.filter_by(login=username).first()
        login_user(user, True)
        if ("SCRIPT_NAME" in request.environ) and request.environ["SCRIPT_NAME"]:
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
    try:
        password_quality(new)
    except ValueError as err:
        flash(err)
        return redirect(url_for("login.reset"))
    current_user.set_password(new)
    flash("You have successfully changed your password!")
    return redirect(url_for("user.user_index"))


@bp.route("/login", methods=["GET", "POST"])
@bp.route("/login.html", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("user.user_index"))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html", form=form)

    form.validate_on_submit()
    username = form.login.data
    password = form.passw.data
    user = User.query.filter_by(login=username).first()
    debug(user)
    if not user:
        flash("User '%s' does not exists" % username)
        return redirect(url_for("login.login"))
    if user.hash:
        check = user.check_password(password)
    else:
        check = ssh_login(username, password)
    if not check:
        flash("Invalid password")
        return redirect(url_for("login.login"))
    login_user(user, True)
    g.name = username
    if not user.hash and not user.first_login:
        flash("Think about set new password at %s" % url_for("login.reset",
                                                             _external=True))
    if user.first_login:
        return redirect(url_for("login.reset"))
    return redirect(url_for("user.user_index"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login.login"))
