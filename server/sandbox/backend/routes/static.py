from flask import Blueprint, send_from_directory, make_response
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "static"

static_rp = Blueprint("static", __name__, url_prefix="/static")


@static_rp.route("/", methods=["GET"])
def test():
    return "Service is running"


@static_rp.route("/ping", methods=["GET"])
def ping():
    return "pong"


@static_rp.route("/static/<path>", methods=["GET"])
def static(path):
    response = make_response(send_from_directory(
        directory=STATIC_DIR,
        path=path,
    ))
    response.headers["Content-Disposition"] = f"attachment; filename={path}"
    return response
