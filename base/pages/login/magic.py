from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from logging import warning, debug, error
from flask import current_app


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def ssh_login(login, password):
    auth = False
    login_servers = current_app.config.get("LOGIN_SERVER", None)
    if not login_servers:
        error("Configuration has no LOGIN_SERVER option set")
        return False
    if not isinstance(login_servers, list):
        warning("Option LOGIN_SERVER has to be a list")
        debug("Converting string to list with comma as separator")
        login_servers = login_servers.split(",")
    debug("Resulting server list: %s" % login_servers)
    for host in login_servers:
        host = host.strip()
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
            error("Exception connecting to %s" % host)
            continue
        finally:
            client.close()
    debug("Authenticated: %s" % auth)
    return auth
