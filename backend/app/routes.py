from flask import Blueprint, jsonify

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health():
    """Simple check so the frontend can confirm the backend is reachable."""
    return jsonify({"status": "ok", "message": "FocusFlow API is running"})


@api.route("/tasks", methods=["GET"])
def get_tasks():
    """Placeholder endpoint — replace with real DB-backed tasks later."""
    tasks = [
        {"id": 1, "title": "Learn FastAPI", "completed": False},
        {"id": 2, "title": "Revise BERT", "completed": False},
        {"id": 3, "title": "Work on project", "completed": False},
    ]
    return jsonify(tasks)
