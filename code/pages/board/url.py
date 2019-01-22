from flask import render_template, request, redirect, url_for, g, flash, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from code.pages.board import bp


@bp.route("/board/list", methods=["POST"])
def web_board_list():
    from code.database.schema import Extend

    ext_list = Extend().query.all()
    result = list(map(lambda x: x.to_dict(), ext_list))
    return jsonify({"data": result})


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
def web_board():
    return render_template("board.html")
