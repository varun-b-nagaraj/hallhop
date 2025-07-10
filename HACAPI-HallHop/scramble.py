import os
import redis
import json
import certifi
import uuid
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from supabase import create_client

load_dotenv()

# --- AES-GCM Setup ---
AES_KEY = os.getenv("AES_KEY")  # Must be 32 bytes for AES-256
if not AES_KEY:
    raise ValueError("Missing AES_KEY in environment")
AES_KEY = bytes.fromhex(AES_KEY)
aesgcm = AESGCM(AES_KEY)

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs=certifi.where()
)

# --- Encryption & Storage ---
def encrypt_data(data: dict) -> str:
    nonce = os.urandom(12)  # GCM standard nonce size
    plaintext = json.dumps(data).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return json.dumps({
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex()
    })

def decrypt_data(payload: str) -> dict:
    parsed = json.loads(payload)
    nonce = bytes.fromhex(parsed["nonce"])
    ciphertext = bytes.fromhex(parsed["ciphertext"])
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(decrypted.decode())

def store_credentials(session_id, username, password, base_url, user_id=None):
    plain_data = {
        "username": username,
        "password": password,
        "base_url": base_url
    }
    if user_id:
        plain_data["user_id"] = user_id

    encrypted_payload = encrypt_data(plain_data)

    record_id = str(uuid.uuid4())
    supabase.table("secure_sessions").insert({
        "id": record_id,
        "session_id": session_id,
        "encrypted": encrypted_payload
    }).execute()

    redis_client.setex(session_id, 900, record_id)

def get_credentials(session_id):
    record_id = redis_client.get(session_id)
    if not record_id:
        return None

    record_id = record_id.decode()
    result = supabase.table("secure_sessions").select("encrypted").eq("id", record_id).limit(1).execute()
    if not result.data:
        return None

    encrypted_payload = result.data[0]["encrypted"]
    return decrypt_data(encrypted_payload)
