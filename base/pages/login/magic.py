"""Login-related utilities: password strength checking and SSH-based
authentication against remote login servers.
"""

from logging import debug, error, warning
from re import search

from flask import current_app
from paramiko import AuthenticationException, AutoAddPolicy, SSHClient

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def password_errors(password):
    """Check the strength of a password and return error messages.

    A password is considered strong if it is:
    - 8 to 128 characters long
    - Contains at least one digit, one uppercase letter, one lowercase
      letter, and one special (non-word) character

    Based on https://stackoverflow.com/questions/16709638/

    Args:
        password: The password string to check.

    Returns:
        An error message string if the password is weak, or None if
        it passes all checks.
    """
    if len(password) < 8:
        return "Password must be 8 or more characters!"
    if len(password) > 128:
        return "Password must be less then 128 characters!"
    if not search(r"\d", password):
        return "Password must contain at least one digit!"
    if not search(r"[A-Z]", password):
        return "Password must contain at least 1 uppercase letter!"
    if not search(r"[a-z]", password):
        return "Password must contain at least 1 lowercase letter!"
    if not search(r"\W", password):
        return "Password must contain at least 1 special character!"
    return None


def ssh_login(login, password):
    """Authenticate a user via SSH against configured login servers.

    Tries each server in the ``LOGIN_SERVER`` configuration list until
    one returns a successful authentication.

    Args:
        login: Username to authenticate.
        password: Password to authenticate with.

    Returns:
        True if authentication succeeded on any server, False otherwise.
    """
    auth = False
    login_servers = current_app.config.get("LOGIN_SERVER", None)
    port = current_app.config.get("SSH_PORT", 22)
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
            client.connect(
                host,
                username=login,
                password=password,
                port=port,
                allow_agent=False,
                look_for_keys=False,
            )
            if client.get_transport().is_authenticated():
                auth = True
        except AuthenticationException:
            warning("Wrong password to server %s" % host)
            continue
        except Exception as err:
            error("Exception connecting to %s: %s" % (host, err))
            continue
        finally:
            client.close()
    debug("Authenticated: %s" % auth)
    return auth