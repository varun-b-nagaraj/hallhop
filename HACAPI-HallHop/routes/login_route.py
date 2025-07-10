from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from hac.session import HACSession
from extensions import limiter
from uuid import uuid4
from scramble import store_credentials
import logging

login_bp = Blueprint("login", __name__)
logger = logging.getLogger(__name__)

@login_bp.route("/api/login", methods=["POST"], strict_slashes=False)
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    base_url = data.get("base_url", "https://accesscenter.roundrockisd.org/")

    if not username or not password:
        logger.warning("Login attempt with missing username or password")
        return jsonify({"error": "Missing username or password"}), 400

    # Step 1: Authenticate with HAC
    try:
        session = HACSession(username, password, base_url)
        if not session.login():
            logger.warning(f"Invalid credentials for user: {username}")
            return jsonify({"error": "Invalid credentials or HAC login failed"}), 401
    except ValueError as ve:
        logger.warning(f"ValueError during login for user {username}: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception(f"Unexpected error during login for user {username}")
        return jsonify({"error": f"Unexpected login failure: {str(e)}"}), 500

    # Step 2: Generate session ID and user ID, store encrypted credentials
    session_id = str(uuid4())
    user_id = str(uuid4())  # Optional: replace with a real hash or database user ID later

    try:
        store_credentials(session_id, username, password, base_url, user_id=user_id)
    except Exception as e:
        logger.exception(f"Failed to store credentials for user {username}")
        return jsonify({"error": f"Failed to store session credentials: {str(e)}"}), 500

    # Step 3: Generate JWT with session info
    token = create_access_token(identity=session_id, additional_claims={
        "username": username,
        "base_url": base_url,
        "user_id": user_id
    })

    logger.info(f"✅ Successful login for user: {username}")
    return jsonify(token=token), 200
