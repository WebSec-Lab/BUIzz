# routes/__init__.py
from .render import sandbox_render
from .report import report_pp
from .static import static_rp
def register_blueprints(app):
    app.register_blueprint(sandbox_render)
    app.register_blueprint(report_pp)
    app.register_blueprint(static_rp)
   
