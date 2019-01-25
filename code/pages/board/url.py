from flask import render_template, request, jsonify
from flask_login import login_required
from code.pages import ProjectLog, check_int, check_str
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


@bp.route("/board/accept", methods=["POST"])
@login_required
def web_board_accept():
    from code import db

    record = board_action()
    record.accepted = True
    db.session.commit()
    ProjectLog(record.project).accept(record)
    return jsonify({"update": record.to_dict()})


@bp.route("/board/reject", methods=["POST"])
@login_required
def web_board_reject():
    from code import db

    record = board_action()
    record.accepted = False
    db.session.commit()
    ProjectLog(record.project).reject(record)
    return jsonify(record.to_dict())


def board_action():

    from code.database.schema import Extend

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    eid = check_int(data["eid"])
    note = check_str(data["comment"])

    extend = Extend().query.filter(Extend.id == eid).one()
    if not extend:
        raise ValueError("No extension with id '%s' found" % eid)
    extend.processed = True
    extend.decision = note
    return extend
