import os
import json
import hmac
import hashlib
import uuid
from datetime import datetime, timezone

def submit_prospect_to_mendix(prospect_data, analysis_data):
    """
    Final completion trigger. Structures the JSON, calculates 
    the HMAC signature, and prepares the POST request.
    """
    # 1. Structure the initial payload (with a placeholder for the hash)
    payload = {
        "event_metadata": {
            "source_system": "SENTRY-ALPHA-1",
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "security_hash": "PENDING" 
        },
        "prospect_data": prospect_data,
        "sentry_analysis": analysis_data
    }

    # 2. Convert to string for hashing
    # SOC 2 Tip: Ensure consistent serialization (no extra spaces)
    payload_string = json.dumps(payload, sort_keys=True)
    
    # 3. Calculate HMAC-SHA256
    secret = os.getenv("MENDIX_HMAC_SECRET", "default_secret_for_dev")
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 4. Insert the real hash into the payload
    payload["event_metadata"]["security_hash"] = signature

    # In a real scenario, you would use httpx.post here.
    # For now, we return the verified payload for the agent to 'confirm'.
    print(f"DEBUG: Secure Payload Generated with Hash: {signature}")
    return json.dumps(payload)