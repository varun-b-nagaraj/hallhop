from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from scramble import redis_client

logout_bp = Blueprint("logout", __name__, url_prefix="/api")

@logout_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    session_id = get_jwt_identity()
    
    try:
        redis_client.delete(session_id)
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500
