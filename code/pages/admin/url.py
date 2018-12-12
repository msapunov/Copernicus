from flask import g, flash, request, redirect, url_for
from code.pages.admin import bp
from flask_login import login_required, login_user


@bp.route("/switch_user", methods=["POST"])
@login_required
def web_switch_user():
    username = request.form.get("switch_user")
    if not username in g.user_list:
        flash("Invalid username: '%s'" % username)
        flash(request.referrer)
        print(request.referrer)
        print(app)
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for("stat.index"))

    from code.database.schema import User

    user = User.query.filter_by(login=username).first()
    login_user(user, True)
    flash("Username: '%s'" % username)
    return redirect(url_for("stat.index"))
