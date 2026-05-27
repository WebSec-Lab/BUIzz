# routes/__init__.py
from .render import xfo_render
from .report import report_pp

def register_blueprints(app):
    app.register_blueprint(xfo_render)
    app.register_blueprint(report_pp)
   
