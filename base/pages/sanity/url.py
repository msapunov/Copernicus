from flask import render_template, jsonify
from flask_login import login_required
from base.pages import grant_access
from base.pages.user import bp
from base.pages.sanity.magic import suspend_expired, warn_expired


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/suspend/expired", methods=["GET"])
@login_required
@grant_access("admin", "tech")
def web_suspend_expired():
    return jsonify(data=list(map(lambda x: x.to_dict(), suspend_expired())))


@bp.route("/warn/expired", methods=["GET"])
@login_required
@grant_access("admin", "tech")
def web_warn_expired():
    return jsonify(data=list(map(lambda x: x.to_dict(), warn_expired())))
