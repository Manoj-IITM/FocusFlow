from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)

    # Allow the Vue dev server (default Vite port) to call this API.
    # Tighten this list before deploying to production.
    CORS(app, resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]}})

    from .routes import api
    from .db import init_db

    init_db()
    app.register_blueprint(api, url_prefix="/api")

    return app
