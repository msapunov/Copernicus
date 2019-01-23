from flask import render_template, request, redirect, url_for, g, flash, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from code.pages.board import bp


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
def web_board():
    from code.database.schema import Extend

    ext_list = Extend().query.filter(Extend.processed == False).all()
    if not ext_list:
        err = "No new project related requests found! Nothing to do"
        return render_template("board.html", error=err)
    result = list(map(lambda x: x.to_dict(), ext_list))
    return render_template("board.html", data=result)
