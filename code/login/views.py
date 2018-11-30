from flask import render_template, request, redirect, url_for
from flask import session
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from code.login import bp

from logging import warning


class LoginForm(Form):
    login = StringField("Login", validators=[DataRequired()])
    passw = PasswordField("Password", validators=[DataRequired()])


def ssh_login(login, password):
    auth = False
    for host in ["login.ccamu.u-3mrs.fr", "login.mesocentre.univ-amu.fr"]:
        client = SSHClient()
        try:
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(host, username=login, password=password, allow_agent=False, look_for_keys=False)
            if client.get_transport().is_authenticated():
                auth = True
                break
        except AuthenticationException:
            warning("Wrong password to server %s" % host)
        finally:
            client.close()
    return auth


@bp.route("/login.html", methods=["GET", "POST"])
def index():
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
