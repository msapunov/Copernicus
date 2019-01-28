from flask import g, flash, request, redirect, url_for, render_template
from code.pages.admin import bp
from flask_login import login_required, login_user


@bp.route("/switch_user", methods=["POST"])
@login_required
def web_switch_user():
    username = request.form.get("switch_user")
    if username not in g.user_list:
        flash("Invalid username: '%s'" % username)
        if request.referrer and (request.referrer in g.url_list):
            return redirect(request.referrer)
        else:
            return redirect(url_for("stat.index"))

    from code.database.schema import User

    user = User.query.filter_by(login=username).first()
    login_user(user, True)
    flash("Username: '%s'" % username)
    return redirect(url_for("user.user_index"))


@bp.route("/admin", methods=["GET", "POST"])
@bp.route("/admin.html", methods=["GET", "POST"])
@login_required
def web_admin():
    result = {}
    return render_template("admin.html", data=result)