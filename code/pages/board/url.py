from flask import render_template, jsonify
from flask_login import login_required
from code.pages import ProjectLog
from code.pages.board import bp
from code.pages.board.magic import board_action, accept_message, reject_message


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


@bp.route("/board/accept", methods=["POST"])
@login_required
def web_board_accept():
    from code import db

    record = board_action()
    record.accepted = True
    db.session.commit()
    ProjectLog(record.project).accept(record)
    #accept_message(record)
    return jsonify(record.to_dict())


@bp.route("/board/ignore", methods=["POST"])
@login_required
def web_board_ignore():
    from code import db

    record = board_action()
    record.accepted = False
    db.session.commit()
    ProjectLog(record.project).ignore(record)
    return jsonify(record.to_dict())


@bp.route("/board/reject", methods=["POST"])
@login_required
def web_board_reject():
    from code import db

    record = board_action()
    record.accepted = False
    db.session.commit()
    ProjectLog(record.project).reject(record)
    reject_message(record)
    return jsonify(record.to_dict())
