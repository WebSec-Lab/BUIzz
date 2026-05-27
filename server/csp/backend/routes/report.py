from flask import Blueprint, request, make_response
from src.mysql_db import insert_into_mysql


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

report_CSP = Blueprint("report", __name__, url_prefix="/report")


@report_CSP.route("/", methods=["GET"])
def test():
    return "Service is running"


@report_CSP.route("/ping", methods=["GET"])
def ping():
    return "pong"


def _field(cookie_name, arg_name=None):
    return (request.cookies.get(cookie_name)
            or request.cookies.get(cookie_name + "1")
            or request.args.get(arg_name or cookie_name))


@report_CSP.route("/report", methods=["POST", "GET", "OPTIONS"])
def main():
    if request.method == "OPTIONS":
        return _cors(make_response("", 204))

    browser_name = _field("browser_name")
    scenario_id  = _field("number_of_scenario", "scenario_id")
    bf           = _field("bf")
    corpus       = _field("corpus")
    interaction  = _field("interaction")

    if bf is None:
        return _cors(make_response("missing bf", 400))

    event_type   = "interaction" if bf == "1" else "corpus"
    corpus_type  = "csp"
    leak         = "fetch"
    violation    = "1"

    result = insert_into_mysql(
        browser_name or "null", scenario_id or "null", corpus or "null",
        event_type, corpus_type, leak, violation, interaction,
    )
    return _cors(make_response(f"report {result}"))
