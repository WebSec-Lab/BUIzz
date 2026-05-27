# routes/__init__.py
from .render import render_PP
from .report import report_pp
from .static import static_PP


def register_blueprints(app):
    app.register_blueprint(render_PP)
    app.register_blueprint(report_pp)
    app.register_blueprint(static_PP)