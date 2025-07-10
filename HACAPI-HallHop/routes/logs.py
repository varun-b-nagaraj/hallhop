from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase import create_client
from scramble import get_credentials
import os
import logging

logs_bp = Blueprint("logs", __name__, url_prefix="/logs")
logger = logging.getLogger(__name__)

# Secure Supabase connection
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

def set_rls_context(user_id):
    """Set Supabase RLS context using set_config() RPC."""
    try:
        supabase.postgrest.rpc("set_config", {
            "key": "app.user_id",
            "value": str(user_id),
            "is_local": True
        }).execute()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set RLS context: {str(e)}")
        return False

@logs_bp.route("/checkout", methods=["POST"])
@jwt_required()
def log_checkout():
    session_id = get_jwt_identity()
    creds = get_credentials(session_id)

    if not creds:
        return jsonify({"error": "Session expired or credentials missing"}), 401

    user_id = creds.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id missing from credentials"}), 400

    payload = request.get_json()
    logger.info(f"📥 Checkout Payload: {payload}")

    required_fields = ["student_id", "student_name", "class_name", "period", "room", "teacher", "checkout_time"]
    if not all(field in payload for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    record = {
        "student_id":    payload["student_id"],
        "student_name":  payload["student_name"],
        "class_name":    payload["class_name"],
        "period":        int(payload["period"]),
        "room":          payload["room"],
        "teacher":       payload["teacher"],
        "checkout_time": payload["checkout_time"],
        "user_id":       user_id
    }

    if not set_rls_context(user_id):
        return jsonify({"error": "Failed to set RLS context"}), 500

    try:
        res = supabase.table("checkouts").insert(record).execute()
        if res.data:
            logger.info(f"✅ Supabase insert success: {res.data[0]}")
            return jsonify(res.data[0]), 201
        else:
            logger.warning("⚠️ Supabase insert returned no data")
            return jsonify({"error": "Insert failed"}), 500
    except Exception as e:
        logger.exception("❌ Exception during Supabase insert")
        return jsonify({"error": str(e)}), 500

@logs_bp.route("/checkin", methods=["POST"])
@jwt_required()
def log_checkin():
    session_id = get_jwt_identity()
    creds = get_credentials(session_id)

    if not creds:
        return jsonify({"error": "Session expired or credentials missing"}), 401

    user_id = creds.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id missing from credentials"}), 400

    payload = request.get_json()
    logger.info(f"📥 Checkin Payload: {payload}")

    if not all(k in payload for k in ("checkout_id", "checkin_time", "duration_sec")):
        return jsonify({"error": "Missing checkout_id, checkin_time, or duration_sec"}), 400

    if not set_rls_context(user_id):
        return jsonify({"error": "Failed to set RLS context"}), 500

    try:
        res = supabase.table("checkouts") \
            .update({
                "checkin_time": payload["checkin_time"],
                "duration_sec": payload["duration_sec"]
            }) \
            .eq("id", payload["checkout_id"]) \
            .execute()

        if res.data:
            logger.info(f"✅ Supabase update success: {res.data}")
            return jsonify(res.data), 200
        else:
            logger.warning("⚠️ Supabase update returned no data")
            return jsonify({"error": "Update failed"}), 500
    except Exception as e:
        logger.exception("❌ Exception during Supabase update")
        return jsonify({"error": str(e)}), 500
