from flask import render_template, flash
from flask_login import login_required, current_user
from code.pages.stat import bp
from code.pages.stat.magic import ssh_wrapper
from code.utils import bytes2human, accounting_start
from datetime import datetime as dt


@bp.route('/', methods=["GET", "POST"])
@bp.route('/index', methods=["GET", "POST"])
@login_required
def index():
    jobs = get_jobs()
    scratch = get_scratch()
    data = {"jobs": jobs, "scratch": scratch}
    return render_template("stat.html", data=data)

def get_scratch():
    cmd = "beegfs-ctl --getquota --csv --uid %s" % current_user.login
    result, err = ssh_wrapper(cmd)
    if not result:
        flash("No scratch space info found")

    info = result[1]
    name, uid, used, total, files, hard = info.split(",")
    usage = "{0:.1%}".format(float(used) / float(total))
    free = float(total) - float(used)
    return {"usage": usage, "total": total, "used": used, "free": free,
            "used_label": bytes2human(used), "free_label": bytes2human(free)}

def get_jobs():
    start = accounting_start()
    end = dt.now().strftime("%m/%d/%y-%H:%M")
    cmd = ["sacct", "-nPX",
           "--format=JobID,State,Start,Account,JobName,CPUTime,Partition",
           "--start=%s" % start, "--end=%s" % end, "-u",
           current_user.login]
    run = " ".join(cmd)

    result, err = ssh_wrapper(run)

    if not result:
        flash("No jobs found")
    jobs = []
    for job in result:
        tmp = {}
        job = job.strip().split("|")
        tmp["id"] = int(job[0])
        tmp["project"] = job[3]
        tmp["state"] = job[1]
        tmp["partition"] = job[6]
        tmp["date"] = job[2]
        tmp["name"] = job[4]
        tmp["duration"] = job[5]
        jobs.append(tmp)
    jobs = sorted(jobs, key=lambda x: x["id"], reverse=True)
    result = jobs[0:10]
    return result
