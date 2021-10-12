from flask import current_app
from datetime import datetime as dt
from unicodedata import normalize
from tempfile import gettempdir, mkdtemp
from os import walk
from os.path import join as join_dir, exists
from base64 import b64encode
import logging as log


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
    else:
        dir_name = mkdtemp(prefix=prefix)
        log.debug("Temporary directory created: %s" % dir_name)
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
    if not file_name:
        file_name = file.filename
    else:
        if "." not in file_name and "." not in file.filename:
            file_name = "%s.unknown" % file_name
        elif "." not in file_name and "." in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            log.debug("Deducted file extensions: %s" % ext)
            file_name = "%s.%s" % (file_name, ext)
    name = join_dir(directory, file_name)
    log.debug("Saving file from incoming request to: %s" % name)
    file.save(name)
    return {"saved_name": file_name, "incoming_name": file.filename}


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word


"""
Bytes-to-human / human-to-bytes converter.
Based on: http://goo.gl/kTQMs
Working with Python 2.x and 3.x.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

SYMBOLS = {
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                      'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi', 'zebi',
                'yobi'),
}


def bytes2human(n, arrangment='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, arrangment="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return arrangment % locals()
    return arrangment % dict(symbol=symbols[0], value=n)
