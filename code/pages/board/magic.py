from flask import request
from code.pages import check_int, check_str


def board_action():

    from code.database.schema import Extend

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    eid = check_int(data["eid"])
    note = check_str(data["comment"])

    extend = Extend().query.filter(Extend.id == eid).one()
    if not extend:
        raise ValueError("No extension with id '%s' found" % eid)
    if extend.processed:
        raise ValueError("This request has been already processed")
    extend.processed = True
    extend.decision = note
    return extend
