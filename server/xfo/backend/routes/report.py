from flask import Blueprint, request
from src.mysql_db import insert_into_mysql

report_pp = Blueprint("report", __name__, url_prefix="/report")


@report_pp.route("/", methods=["GET"])
def test():
    return "Service is running"


@report_pp.route("/ping", methods=["GET"])
def ping():
    return "pong"


def _field(cookie_name, arg_name=None):
    return (request.cookies.get(cookie_name)
            or request.cookies.get(cookie_name + "1")
            or request.args.get(arg_name or cookie_name))


@report_pp.route("/report", methods=["POST", "GET"])
def main():
    browser_name = _field("browser_name")
    scenario_id  = _field("number_of_scenario", "scenario_id")
    bf           = _field("bf")
    corpus       = _field("corpus")
    interaction  = _field("interaction")

    if bf is None:
        return ("missing bf", 400)

    event_type   = "interaction" if bf == "1" else "corpus"
    corpus_type  = "x-frame-options"
    leak         = "default"
    violation    = request.args.get("leak", "")

    result = insert_into_mysql(
        browser_name or "null", scenario_id or "null", corpus or "null",
        event_type, corpus_type, leak, violation, interaction,
    )
    return f"{result}"
