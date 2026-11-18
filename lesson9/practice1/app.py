"""Flask app mounting User API v1 and v2 blueprints under URI path versions."""

from flask import Flask
from blueprints.v1 import bp as v1_bp
from blueprints.v2 import bp as v2_bp

app = Flask(__name__)
app.register_blueprint(v1_bp, url_prefix=f"/api/v1{v1_bp.url_prefix}")
app.register_blueprint(v2_bp, url_prefix=f"/api/v2{v2_bp.url_prefix}")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
