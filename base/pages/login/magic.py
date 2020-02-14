from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from logging import warning, debug, error
from flask import current_app

import logging as log


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def ssh_login(login, password):
    auth = False
    login_servers = current_app.config.get("LOGIN_SERVER", None)
    if not login_servers:
        return False
    if not isinstance(login_servers, list):
        return False
    for host in login_servers:
        debug("Trying the host: %s" % host)
        client = SSHClient()
        try:
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(host, username=login, password=password,
                           allow_agent=False, look_for_keys=False)
            if client.get_transport().is_authenticated():
                auth = True
        except AuthenticationException:
            warning("Wrong password to server %s" % host)
            continue
        except:
            error("Exception connecting to %s. Trying next server" % host)
            continue
        finally:
            client.close()
    return auth
