from flask import render_template, request, redirect, url_for, g, flash
from flask_login import current_user, login_user, logout_user, login_required
from code.pages.board import bp


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
def web_board():
    return render_template("board.html")