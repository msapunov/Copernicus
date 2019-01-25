from flask_login import current_user


def check_int(raw_int):
    number = int(raw_int)
    if (not number) or (number < 1):
        raise ValueError("Integer must be a positive number: %s" % number)
    return number


def check_str(raw_note):
    note = str(raw_note)
    if (not note) or (len(note) < 1):
        raise ValueError("Provided string can't be empty")
    return note


class ProjectLog:

    def __init__(self, project):
        from code.database.schema import LogDB
        self.log = LogDB(author=current_user, project=project)

    def extend(self, extension):
        self.log.event = "extension request"
        self.log.extension = extension
        self._commit()

    def activate(self, extension):
        self.log.event = "activation request"
        self.log.extension = extension
        self._commit()

    def transform(self, extension):
        self.log.event = "transformation request"
        self.log.extension = extension
        self._commit()

    def accept(self, extension):
        self.log.event = "accept request"
        self.log.extension = extension
        self._commit()

    def reject(self, extension):
        self.log.event = "reject request"
        self.log.extension = extension
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.log)
        db.session.commit()
