from flask import g, render_template
from flask_login import login_required
from code.stat import bp


@bp.route('/', methods=["GET", "POST"])
@bp.route('/index', methods=["GET", "POST"])
@login_required
def index():
    text = "There will be dragons here!"
    return render_template("stat.html", body = text)