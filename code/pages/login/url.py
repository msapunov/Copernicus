from flask import render_template, request, redirect, url_for, g, flash, abort
from flask_login import current_user, login_user, logout_user, login_required
from code.pages.login.magic import ssh_login
from code.pages.login.form import LoginForm
from code.pages.login import bp
from base64 import b64decode

from logging import warning


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
        from code.database.schema import User
        user = User.query.filter_by(login=username).first()
        login_user(user, True)
        urlpath = "/%s" % urlpath
        print(urlpath)
        return redirect(urlpath, code=307)
    return None


@bp.route("/login", methods=["GET", "POST"])
@bp.route("/login.html", methods=["GET", "POST"])
def login():

    from code.database.schema import User

    if current_user.is_authenticated:
        return redirect(url_for("user.user_index"))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html", form=form)

    form.validate_on_submit()
    username = form.login.data
    password = form.passw.data
    if not ssh_login(username, password):
        flash("Invalid username or password")
        return redirect(url_for("login.login"))

    user = User.query.filter_by(login=username).first()
    warning(user)
    login_user(user, True)
    g.name = username
    return redirect(url_for("user.user_index"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login.login"))
