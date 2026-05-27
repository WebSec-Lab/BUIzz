from flask import Blueprint, send_from_directory
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JS_DIRECTORY = BASE_DIR.parent / "static" / "js"

static_PP = Blueprint("static", __name__, url_prefix="/static")


@static_PP.route("/", methods=["GET"])
def test():
    return "Service is running"


@static_PP.route("/ping", methods=["GET"])
def ping():
    return "pong"


@static_PP.route("/static.js", methods=["GET"])
def main():
    return send_from_directory(
        directory=JS_DIRECTORY,
        path="static.js",
        mimetype='application/javascript'
    )
