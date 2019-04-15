from flask import render_template, jsonify
from flask_login import login_required
from code.pages import ProjectLog, check_json, check_int, check_str
from code.pages.board import bp
from code.pages.board.magic import board_action, create_resource
from code.pages.project.magic import get_project_record
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

    extension = False
    if check_str(data["extension"]).lower() == "true":
        extension = True

    if record.extend != extension:
        record.extend = extension
        record.decision += "\nSet extension option to %s by hands"

    project = get_project_record(record.project.id)
    from code import db

    if record.extend:
        project.resources.treated=False
        project.resources.cpu += cpu
    else:
        project.resources.valid = False
        resource = create_resource(project, cpu)
        db.session.add(resource)
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
