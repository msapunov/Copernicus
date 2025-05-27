from werkzeug.utils import secure_filename
from unicodedata import normalize
from os.path import join as join_dir
from logging import debug


def form_error_string(err_dict):
    result = []
    for key, value in err_dict.items():
        if key == "csrf_token" and value == ["The CSRF token has expired."]:
            result.append("Your session has expired! Please, reload the page")
            continue
        for err in value:
            result.append("%s: %s" % (key, err))
    return "\n".join(result)


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
    if file.filename == "":
        raise ValueError("No selected file")
    debug("File name from incoming request: %s" % file.filename)
    if not file_name:
        file_name = file.filename
    else:
        if "." not in file_name and "." not in file.filename:
            file_name = "%s.unknown" % file_name
        elif "." not in file_name and "." in file.filename:
            ext = file.filename.rsplit(".", 1)[1].lower()
            debug("Deducted file extensions: %s" % ext)
            file_name = "%s.%s" % (file_name, ext)
    name = join_dir(directory, file_name)
    debug("Saving file from incoming request to: %s" % name)
    file.save(name)
    return {"saved_name": file_name, "incoming_name": file.filename}


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word
