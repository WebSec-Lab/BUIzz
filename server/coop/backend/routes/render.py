import re
import urllib.parse
from flask import Blueprint, render_template, make_response, request

coop_pp = Blueprint("coop", __name__, url_prefix="/coop")


def _inject_tracking(html, tracking):
    params = urllib.parse.urlencode({k: v for k, v in tracking.items() if v})
    if not params:
        return html

    def add_params(m):
        url = m.group(0)
        if '#' in url:
            url = url.split('#', 1)[0]
        sep = '&' if '?' in url else '?'
        return f"{url}{sep}{params}"

    return re.sub(
        r'https?://[^\s"\'<>]*(?:/static/static\.js|/report/report/?)[^\s"\'<>]*',
        add_params,
        html,
    )


@coop_pp.route("/", methods=["GET"])
def test():
    return "Service is running"


@coop_pp.route("/ping", methods=["GET"])
def ping():
    return "pong"


@coop_pp.route("/<page>", methods=["GET"])
def main(page):
    if not page.endswith(".html"):
        page = page + ".html"

    coop = request.args.get('coop')
    tracking = {
        'browser_name': request.args.get('browser_name', ''),
        'scenario_id':  request.args.get('scenario_id', ''),
        'bf':           request.args.get('bf', ''),
        'corpus':       request.args.get('corpus', ''),
    }

    html = render_template(page)
    html = _inject_tracking(html, tracking)

    response = make_response(html)
    response.headers['Cross-Origin-Opener-Policy'] = f"{coop}"
    return response
