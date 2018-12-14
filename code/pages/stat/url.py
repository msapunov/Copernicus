from flask import render_template, flash
from flask_login import login_required, current_user
from code.pages.stat import bp
from code.pages.stat.magic import ssh_wrapper


@bp.route('/', methods=["GET", "POST"])
@bp.route('/index', methods=["GET", "POST"])
@login_required
def index():

    cmd = ["sacct", "-nPX",
           "--format=JobID,State,Start,Account,JobName,CPUTime,Partition",
           "--start=02/15/18-00:00", "--end=12/13/18-15:35", "-u",
           current_user.login]
    run = " ".join(cmd)

    result, err = ssh_wrapper(run)

    if not result:
        flash("No jobs found")
    data = {"jobs": []}
    for job in result:
        tmp = {}
        job = job.strip().split("|")
        tmp["id"] = job[0]
        tmp["project"] = job[3]
        tmp["state"] = job[1]
        tmp["partition"] = job[6]
        tmp["date"] = job[2]
        tmp["name"] = job[4]
        tmp["duration"] = job[5]
        data["jobs"].append(tmp)
    return render_template("stat.html", data=data)
