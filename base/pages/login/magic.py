from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from logging import warning, debug, error


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def ssh_login(login, password):
    auth = False
    for host in ["login.ccamu.u-3mrs.fr", "login.mesocentre.univ-amu.fr"]:
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
