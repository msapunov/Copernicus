from flask import render_template, request, redirect, url_for
from flask import session
from flask_login import current_user, login_user, logout_user, login_required
from code.login.magic import ssh_login
from code.login.form import LoginForm
from code.login import bp

from logging import warning


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        pass


@bp.route("/login.html", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html", form=form)
    form.validate_on_submit()
    login = form.login.data
    password = form.passw.data
    if not ssh_login(login, password):
        return redirect(url_for("/login.html"))
    session["login"] = login
    warning("RENDERING THE PAGE!")
    return "True"


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("project.index"))