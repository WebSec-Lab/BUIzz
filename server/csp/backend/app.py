from flask import Flask, render_template, make_response
from routes import register_blueprints

app = Flask(__name__, static_folder='assets')
register_blueprints(app)


@app.route("/index", methods=["GET", "POST"])
def main():
    return "Service is running"


@app.route("/", methods=["GET", "POST"])
def index():
    return make_response(render_template("index.html"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5221)
