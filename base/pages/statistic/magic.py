import logging as log
import flask_excel as excel

from flask import current_app
from base.functions import project_get_info


def dump_projects_database(extension_type):
    if extension_type not in ["csv", "ods", "xls", "xlsx"]:
        raise ValueError("Unsupported format: %s" % extension_type)
    dirty_projects = project_get_info(every=True, usage=False)
    projects = []
    for project in dirty_projects:
        if not project.responsible:
            continue
        if not project.ref:
            continue
        projects.append(project)
    output = sorted(list(map(lambda x: x.to_dict(), projects)), key=lambda x: x["id"])
    excel.init_excel(current_app)
    filename = "projects." + extension_type
    return excel.make_response_from_records(output, file_type=extension_type, file_name=filename)