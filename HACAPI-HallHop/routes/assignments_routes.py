from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from hac.session import HACSession
from scramble import get_credentials
import logging

logger = logging.getLogger(__name__)
assignments_bp = Blueprint("assignments", __name__, url_prefix="/api")

def _get_hac_session_from_jwt():
    """Securely fetch credentials and initialize HAC session."""
    session_id = get_jwt_identity()
    creds = get_credentials(session_id)

    if not creds:
        logger.warning(f"Session expired or credentials missing for session_id: {session_id}")
        return None, (jsonify({"error": "Session expired or credentials missing"}), 401)

    username = creds.get("username")
    password = creds.get("password")
    base_url = creds.get("base_url")

    if not all([username, password, base_url]):
        logger.error(
            f"Incomplete credentials for session_id: {session_id}. "
            f"username: {bool(username)}, password: {bool(password)}, base_url: {bool(base_url)}"
        )
        return None, (jsonify({"error": "Incomplete credentials found in session"}), 400)

    try:
        session = HACSession(username, password, base_url)
        if not session.login():
            logger.warning(f"HAC login failed for user: {username}")
            return None, (jsonify({"error": "HAC login failed"}), 401)
        return session, None
    except Exception as e:
        logger.exception(f"Exception initializing HAC session for user: {username}")
        return None, (jsonify({"error": str(e)}), 500)

@assignments_bp.route("/getAssignments", methods=["GET"])
@jwt_required()
def get_assignments():
    session, error = _get_hac_session_from_jwt()
    if error:
        return error

    class_name = request.args.get("class", "").strip()

    try:
        if class_name:
            logger.info(f"Fetching assignments for class '{class_name}' for user: {session.username}")
            assignments = session.get_assignment_class(class_name)
        else:
            logger.info(f"Fetching all assignments for user: {session.username}")
            assignments = session.fetch_class_assignments()

        if assignments is None:
            logger.warning(f"No assignments found for user: {session.username}" +
                           (f" in class '{class_name}'" if class_name else ""))
            return jsonify({"error": "No assignments found or failed to retrieve"}), 404

        return jsonify(assignments), 200
    except Exception as e:
        logger.exception(f"Exception in /getAssignments for user: {session.username}")
        return jsonify({"error": str(e)}), 500
