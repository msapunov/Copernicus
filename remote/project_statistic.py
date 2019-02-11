from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from datetime import datetime as dt
from logging import error, debug
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile


SSH_SERVER="web.mesocentre.univ-amu.fr"
SSH_USERNAME="copenicus"
SSH_KEY="/opt/utils/.ssh/ssh_key"

ACC_START_DAY = 15
ACC_START_MONTH = 2


def accounting_start():
    DAY = ACC_START_DAY
    MONTH = ACC_START_MONTH

    now = dt.now()
    year = now.year
    month = now.month
    day = now.day
    if (month < MONTH) or ((month == MONTH) and (day <= DAY)):
        year -= 1
    year -= 2000
    mth = str(MONTH).zfill(2)
    day = str(DAY).zfill(2)
    return "%s/%s/%s-00:00" % (mth, day, year)


START=accounting_start()
END=dt.now().strftime("%m/%d/%y-%H:%M")


def ssh_wrapper(cmd):
    debug("ssh_wrapper(%s)" % cmd)
    host = SSH_SERVER
    login = SSH_USERNAME
    key_file = SSH_KEY
    key = RSAKey.from_private_key_file(key_file)

    debug("Connecting to %s with login %s and key %s" % (host, login, key_file))
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=login, pkey=key)
    except AuthenticationException:
        error("Failed to connect to %s under using %s with key '%s'"
              % (host, login, key_file))
        client.close()

    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.readlines()
    errors = stderr.readlines()
    client.close()

    return output, errors


def get_statistic():
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours",
           "-nP", "format=Account,Login,Used", "start=%s" % START, "end=%s"
           % END]
    debug("Executing command: %s" % " ".join(cmd))
    output = run(cmd, stdout=PIPE)
    if output.returncode != 0:
        raise ValueError("Failed to execute command %s" % " ".join(cmd))
    return output.stdout

def save_statistic():
    stat = get_statistic()
    debug("Got statistic: %s" % stat)
    with NamedTemporaryFile(mode="w", prefix="copernicus") as fd:
        fd.write(stat)
        f_name = fd.name
        ssh_wrapper(cmd)
