from unicodedata import normalize


def form_error_string(err_dict):
    result = []
    for key, value in err_dict.items():
        if key == "csrf_token" and value == ["The CSRF token has expired."]:
            result.append("Your session has expired! Please, reload the page")
            continue
        for err in value:
            result.append("%s: %s" % (key, err))
    return "\n".join(result)


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word
