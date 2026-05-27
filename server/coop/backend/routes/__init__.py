# routes/__init__.py
from .render import coop_pp
from .report import report_pp

def register_blueprints(app):
    app.register_blueprint(coop_pp)
    app.register_blueprint(report_pp)
   
