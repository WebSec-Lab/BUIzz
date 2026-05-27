import re
import urllib.parse
from flask import Blueprint, render_template, make_response, request

render_CSP = Blueprint("render", __name__, url_prefix="/render")


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


@render_CSP.route("/", methods=["GET"])
def test():
    return "Service is running"


@render_CSP.route("/ping", methods=["GET"])
def ping():
    return "pong"


@render_CSP.route("/<page>", methods=["GET"])
def main(page):
    if not page.endswith(".html"):
        page = page + ".html"

    tracking = {
        'browser_name': request.args.get('browser_name', ''),
        'scenario_id':  request.args.get('scenario_id', ''),
        'bf':           request.args.get('bf', ''),
        'corpus':       request.args.get('corpus', ''),
    }

    html = render_template("/output/" + page)
    html = _inject_tracking(html, tracking)

    response = make_response(html)
    csp = request.args.get("csp")
    if csp:
        csp = csp.encode("ascii", errors="ignore").decode("ascii")
        if csp:
            response.headers["Content-Security-Policy"] = csp
    return response
