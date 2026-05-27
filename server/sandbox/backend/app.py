from flask import Flask, render_template
from routes import register_blueprints

app = Flask(__name__)
register_blueprints(app)

@app.route("/index", methods=["GET", "POST"])
def main():
    return "Service is running"

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5021)
