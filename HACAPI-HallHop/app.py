from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from routes import register_routes
from dotenv import load_dotenv
from hac.session import HACSession
from datetime import timedelta
import os

# Supabase
from supabase import create_client

# JWT
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity

# Rate Limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_identity_or_ip():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity() or get_remote_address()
    except Exception:
        return get_remote_address()

def create_app():
    app = Flask(__name__)
    
    # JWT Config
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")  # Change in prod
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)  # 🔐 Token expiry set here

    # Initialize JWT
    jwt = JWTManager(app)

    # Fix for reverse proxy (Render, Heroku, etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Enable CORS
    CORS(app)

    # Apply rate limiting
    limiter = Limiter(
        get_identity_or_ip,
        app=app,
        default_limits=["100 per hour"]
    )

    # Register routes (you can apply limiter inside those files too)
    register_routes(app)

    # Optional: Enforce HTTPS in production
    if os.getenv("FLASK_ENV") != "development":
        @app.before_request
        def enforce_https():
            if not request.is_secure:
                return redirect(request.url.replace("http://", "https://"), code=301)

    # Health check / welcome
    @app.route("/")
    def home():
        return jsonify({
            "success": True,
            "message": "Welcome to the HAC API."
        })

    # Optional: Rate limit error handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded"}), 429

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
