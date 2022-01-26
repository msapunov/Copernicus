from flask import current_app
from datetime import datetime as dt
from unicodedata import normalize
from tempfile import gettempdir, mkdtemp
from os import walk
from os.path import join as join_dir, exists
from base64 import b64encode
from magic import from_file
import logging as log
from logging import debug


def is_text(name):
    name = str(name)
    mime = from_file(name, mime=True)
    if "text/" in mime:
        return True
    return False


def form_error_string(err_dict):
    result = []
    for key, value in err_dict.items():
        if key == "csrf_token" and value == ["The CSRF token has expired."]:
            result.append("Your session has expired! Please, reload the page")
            continue
        for err in value:
            result.append("%s: %s" % (key, err))
    return "\n".join(result)


def image_string(name):
    img_path = join_dir(current_app.instance_path, name)
    if not exists(img_path):
        raise ValueError("Image %s doesn't exists" % img_path)
    with open(img_path, "rb") as img_file:
        return b64encode(img_file.read()).decode("ascii")


def get_tmpdir(app):
    """
    Check if application specific directory has been already created and create
    said directory if it doesn't exists. If directory started with prefix is
    already there the function returns first element from the directory list
    :param app: Current flask application
    :return: String. Name of the temporary application specific directory.
    """
    prefix = get_tmpdir_prefix(app)
    dirs = [x[0] for x in walk(gettempdir())]
    is_exists = list(filter(lambda x: True if prefix in x else False, dirs))
    if is_exists:
        dir_name = is_exists[0]
        log.debug("Found existing directory: %s" % dir_name)
        debug("Found existing directory: %s" % dir_name)
    else:
        dir_name = mkdtemp(prefix=prefix)
        log.debug("Temporary directory created: %s" % dir_name)
        debug("Temporary directory created: %s" % dir_name)
    return dir_name


def get_tmpdir_prefix(app):
    """
    Construct the prefix for the temporary directory based on SECRET_KEY
    parameter from configuration file
    :param app: Current application
    :return: String
    """
    return "%s_copernicus_" % app.config.get("SECRET_KEY", "XXX")[0:3]


def save_file(req, directory, file_name=False):
    """
    Saving incoming file HTTP request to provided directory under original or
    provided filename
    :param req: Incoming file HTTP request
    :param directory: Directory where to save the file from incoming request
    :param file_name: Default is False. By default the file is saved under name
    extracted from file http request.
    :return: Dictionary
    """
    if "file" not in req.files:
        raise ValueError("File expected!")
    file = req.files["file"]
    if file.filename == '':
        raise ValueError("No selected file")
    log.debug("File name from incoming request: %s" % file.filename)
    debug("File name from incoming request: %s" % file.filename)
    if not file_name:
        file_name = file.filename
    else:
        if "." not in file_name and "." not in file.filename:
            file_name = "%s.unknown" % file_name
        elif "." not in file_name and "." in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            log.debug("Deducted file extensions: %s" % ext)
            debug("Deducted file extensions: %s" % ext)
            file_name = "%s.%s" % (file_name, ext)
    name = join_dir(directory, file_name)
    log.debug("Saving file from incoming request to: %s" % name)
    debug("Saving file from incoming request to: %s" % name)
    file.save(name)
    return {"saved_name": file_name, "incoming_name": file.filename}


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word
