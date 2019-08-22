from flask import render_template, jsonify
from flask_login import login_required
from base import db
from base.pages import ProjectLog, check_json, check_int, check_str
from base.pages.board import bp
from base.pages.board.magic import get_arguments, create_resource, Extensions
from base.pages.project.magic import get_project_record


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
def web_board():
    extensions_list = Extensions().unprocessed()
    if not extensions_list:
        err = "No new project related requests found! Nothing to do"
        return render_template("board.html", error=err)
    result = list(map(lambda x: x.to_dict(), extensions_list))
    return render_template("board.html", data=result)


@bp.route("/board/history", methods=["POST"])
@login_required
def web_board_history():
    extensions_list = Extensions().history()
    if not extensions_list:
        return jsonify(message="No records found for project extension")
    result = list(map(lambda x: x.to_dict(), extensions_list))
    return jsonify(data=result)


@bp.route("/board/accept", methods=["POST"])
@login_required
def web_board_accept():

    eid, note = get_arguments()
    record = Extensions(eid).accept(note)

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
    record = reject_extension()
    return jsonify(message=ProjectLog(record.project).ignore(record),
                   data={"id": record.id})


@bp.route("/board/reject", methods=["POST"])
@login_required
def web_board_reject():
    record = reject_extension()
    return jsonify(message=ProjectLog(record.project).reject(record),
                   data={"id": record.id})


def reject_extension():
    eid, note = get_arguments()
    return Extensions(eid).reject(note)
