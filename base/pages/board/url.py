from flask import render_template, jsonify
from flask_login import login_required
from base.classes import ProjectLog, Extensions
from base.pages import grant_access
from base.pages.board import bp
from base.pages.board.magic import get_arguments, reject_extension, transform


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/board", methods=["GET", "POST"])
@bp.route("/board.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_board():
    return render_template("board.html")


@bp.route("/board/history", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_history():
    extensions_list = Extensions().history()
    if not extensions_list:
        return jsonify(message="No records found for project extension")
    result = list(map(lambda x: x.to_dict(), extensions_list))
    return jsonify(data=result)


@bp.route("/board/activate/<int:eid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_activate(eid):
    record = Extensions(eid).activate("Activation accepted")
    return jsonify(message=ProjectLog(record.project).accept(record),
                   data={"id": record.id})


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
    record = Extensions(eid).ignore()
    return jsonify(message=ProjectLog(record.project).ignore(record),
                   data={"id": record.id})


@bp.route("/board/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_list():
    extensions_list = Extensions().unprocessed()
    if not extensions_list:
        err = "No new project related requests found! Nothing to do"
        return jsonify(message=err)
    return jsonify(data=list(map(lambda x: x.to_dict(), extensions_list)))


@bp.route("/board/expand/<int:eid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_board_expand(eid):
    record = Extensions(eid).record()
    return render_template("bits/extension_expand_row.html",
                          rec=record.to_dict())
