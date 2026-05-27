import re
import urllib.parse
from flask import Blueprint, render_template, make_response, request

xfo_render = Blueprint("xfo", __name__, url_prefix="/xfo")


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


@xfo_render.route("/", methods=["GET"])
def test():
    return "Service is running"


@xfo_render.route("/ping", methods=["GET"])
def ping():
    return "pong"


@xfo_render.route("/<page>", methods=["GET"])
def main(page):
    if not page.endswith(".html"):
        page = page + ".html"

    xfo = request.args.get('xfo')
    tracking = {
        'browser_name': request.args.get('browser_name', ''),
        'scenario_id':  request.args.get('scenario_id', ''),
        'bf':           request.args.get('bf', ''),
        'corpus':       request.args.get('corpus', ''),
    }

    html = render_template(page)
    html = _inject_tracking(html, tracking)

    response = make_response(html)
    if page == "index.html":
        if xfo is not None:
            response.headers['X-Frame-Options'] = xfo
        else:
            response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
    return response
