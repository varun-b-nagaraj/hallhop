from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from hac.session import HACSession
from scramble import get_credentials
import logging

logger = logging.getLogger(__name__)
report_bp = Blueprint("report", __name__, url_prefix="/api")

def _init_hac_session_from_jwt():
    """Securely initialize a HACSession using encrypted credentials."""
    session_id = get_jwt_identity()
    creds = get_credentials(session_id)

    if not creds:
        logger.warning(f"Session expired or credentials missing for session_id: {session_id}")
        return None, (jsonify({"error": "Session expired or credentials missing"}), 401)

    username = creds.get("username")
    password = creds.get("password")
    base_url = creds.get("base_url")

    if not all([username, password, base_url]):
        logger.error(f"Incomplete credentials for session_id: {session_id}")
        return None, (jsonify({"error": "Incomplete credentials in session"}), 400)

    try:
        session = HACSession(username, password, base_url)
        if not session.login():
            logger.warning(f"HAC login failed for user: {username}")
            return None, (jsonify({"error": "HAC login failed"}), 401)
        return session, None
    except Exception as e:
        logger.exception(f"Exception initializing HAC session for user: {username}")
        return None, (jsonify({"error": str(e)}), 500)

@report_bp.route("/getReport", methods=["GET", "POST"])
@jwt_required()
def get_report():
    session, error = _init_hac_session_from_jwt()
    if error:
        return error

    # Parse student_id from GET or POST
    student_id = request.args.get("student_id") if request.method == "GET" else request.get_json(silent=True, force=True) or {}
    student_id = student_id.get("student_id") if isinstance(student_id, dict) else student_id

    try:
        if student_id:
            logger.info(f"Switching student to {student_id}")
            if not session.switch_student(student_id):
                return jsonify({"error": f"Failed to switch to student {student_id}"}), 400

        report_data = session.get_report()
        if not report_data:
            return jsonify({"error": "Failed to retrieve report"}), 404

        return jsonify(report_data), 200
    except Exception as e:
        logger.exception("Error in /getReport")
        return jsonify({"error": str(e)}), 500

@report_bp.route("/getIpr", methods=["GET"])
@jwt_required()
def get_ipr():
    session, error = _init_hac_session_from_jwt()
    if error:
        return error

    try:
        ipr_data = session.get_progress_report()
        if ipr_data is None:
            return jsonify({"error": "Failed to retrieve progress report"}), 404
        return jsonify(ipr_data), 200
    except Exception as e:
        logger.exception("Error in /getIpr")
        return jsonify({"error": str(e)}), 500
