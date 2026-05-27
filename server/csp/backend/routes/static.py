from flask import Blueprint, send_from_directory, request
from src.mysql_db import insert_into_mysql
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JS_DIRECTORY = BASE_DIR.parent / "static" / "js"

static_CSP = Blueprint("static", __name__, url_prefix="/static")


@static_CSP.route("/", methods=["GET"])
def test():
    return "Service is running"


@static_CSP.route("/ping", methods=["GET"])
def ping():
    return "pong"


@static_CSP.route("/static.js", methods=["GET"])
def main():
    browser_name = (request.cookies.get('browser_name') or request.cookies.get('browser_name1')
                    or request.args.get('browser_name'))
    scenario_id  = (request.cookies.get('number_of_scenario') or request.cookies.get('number_of_scenario1')
                    or request.args.get('number_of_scenario'))
    bf           = (request.cookies.get('bf') or request.cookies.get('bf1')
                    or request.args.get('bf'))
    corpus       = (request.cookies.get('corpus') or request.cookies.get('corpus1')
                    or request.args.get('corpus'))
    event_type = "interaction" if bf == "1" else "corpus"
    insert_into_mysql(browser_name, scenario_id, corpus, event_type, "csp", "script", "1")
    return send_from_directory(
        directory=JS_DIRECTORY,
        path="static.js",
        mimetype='application/javascript'
    )
