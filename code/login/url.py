from flask import render_template, request, redirect, url_for, g, flash
from flask_login import current_user, login_user, logout_user, login_required
from code.login.magic import ssh_login
from code.login.form import LoginForm
from code.login import bp

from logging import warning


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        g.name = current_user


@bp.route("/login.html", methods=["GET", "POST"])
def login():

    from code.database.schema import User

    if current_user.is_authenticated:
        return redirect(url_for("stat.index"))
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
    return redirect(url_for("stat.index"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login.login"))
