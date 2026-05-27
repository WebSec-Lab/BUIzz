# routes/__init__.py
from .render import render_CSP
from .report import report_CSP
from .static import static_CSP


def register_blueprints(app):
    app.register_blueprint(render_CSP)
    app.register_blueprint(report_CSP)
    app.register_blueprint(static_CSP)