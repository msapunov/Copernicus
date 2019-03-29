from flask import render_template, jsonify, current_app
from flask_login import login_required, current_user
from code.pages import ProjectLog, check_json, check_int
from code.pages.board import bp
from code.pages.board.magic import board_action
from code.pages.project.magic import get_project_record
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd
from operator import attrgetter


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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


@bp.route("/board/history", methods=["POST"])
@login_required
def web_board_history():
    from code.database.schema import Extend

    ext_list = Extend().query.all()
    if not ext_list:
        err = "No new project related requests found! Nothing to do"
        return jsonify(message=err)
    sorted_recs = sorted(ext_list, key=attrgetter("created"), reverse=True)
    result = list(map(lambda x: x.to_dict(), sorted_recs))
    return jsonify(data=result)


@bp.route("/board/accept", methods=["POST"])
@login_required
def web_board_accept():

    record = board_action()
    record.accepted = True

    data = check_json()
    cpu = check_int(data["cpu"])
    if (not cpu) or (cpu <= 0):
        cpu = record.hours

    project = get_project_record(record.project.id)

    now = dt.now()
    if project.type == "a":
        month = int(current_app.config["ACC_TYPE_A"])
        ttl = now + rd(month=+month)
    elif project.type == "h":
        month = int(current_app.config["ACC_TYPE_H"])
        ttl = now + rd(month=+month)
    else:  # For project type B
        day = int(current_app.config["ACC_START_DAY"])
        month = int(current_app.config["ACC_START_MONTH"])
        year = now.year + 1
        ttl = dt(year, month, day)

    from code.database.schema import Resources
    from code import db

    resource = Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        project=project.get_name(),
        ttl=ttl,
        treated=False
    )
    db.session.add(resource)
    project.resources.valid = False
    project.resources = resource
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).accept(record),
                   data={"id": record.id})


@bp.route("/board/ignore", methods=["POST"])
@login_required
def web_board_ignore():
    from code import db

    record = board_action()
    record.accepted = False
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).ignore(record),
                   data={"id": record.id})


@bp.route("/board/reject", methods=["POST"])
@login_required
def web_board_reject():
    from code import db

    record = board_action()
    record.accepted = False
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).reject(record),
                   data={"id": record.id})
