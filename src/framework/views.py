from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from src.framework.extensions import db
from src.framework.models import OperationLog, User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@main_bp.route("/api/logs", methods=["POST"])
def create_log():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user_id = data.get("user_id")
    op_type = data.get("operation_type")
    content = data.get("operation_content")
    tx_hash = data.get("tx_hash")

    if not user_id or not op_type:
        return jsonify({"error": "user_id and operation_type are required"}), 400

    # Verify user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    log = OperationLog(
        user_id=user_id,
        operation_type=op_type,
        operation_content=content,
        tx_hash=tx_hash,
    )

    db.session.add(log)
    db.session.commit()

    return jsonify({"message": "Log saved successfully", "log_id": log.id}), 201
