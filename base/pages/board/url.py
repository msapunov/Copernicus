from flask import render_template, jsonify
from flask_login import login_required
from base.classes import ProjectLog
from base.pages import grant_access
from base.pages.board import bp
from base.pages.board.magic import get_arguments, Extensions, reject_extension,\
    ignore_extension, transform


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_board():
    extensions_list = Extensions().unprocessed()
    if not extensions_list:
        err = "No new project related requests found! Nothing to do"
        return render_template("board.html", error=err)
    result = list(map(lambda x: x.to_dict(), extensions_list))
    return render_template("board.html", data=result)


@bp.route("/board/history", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_history():
    extensions_list = Extensions().history()
    if not extensions_list:
        return jsonify(message="No records found for project extension")
    result = list(map(lambda x: x.to_dict(), extensions_list))
    return jsonify(data=result)


@bp.route("/board/transform", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_transform():
    pid, message = transform()
    return jsonify(data={"id": pid}, message=message)


@bp.route("/board/accept", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_accept():
    eid, note, cpu, ext = get_arguments()
    record = Extensions(eid)
    record.cpu = cpu
    record.extend = ext
    record.accept(note)
    return jsonify(message=ProjectLog(record.rec.project).accept(record.rec),
                   data={"id": record.id})


@bp.route("/board/reject/<int:eid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_reject(eid):
    record = reject_extension(eid)
    return jsonify(message=ProjectLog(record.project).reject(record),
                   data={"id": record.id})


@bp.route("/board/ignore/<int:eid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_ignore(eid):
    record = ignore_extension(eid)
    return jsonify(message=ProjectLog(record.project).ignore(record),
                   data={"id": record.id})
