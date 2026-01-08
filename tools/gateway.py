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

    # SOC 2 Tip: Ensure consistent serialization (no extra spaces)
    payload_string = json.dumps(payload, sort_keys=True)
    
    secret = os.getenv("MENDIX_HMAC_SECRET", "sei_systems_secure_gateway_01")
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    payload["event_metadata"]["security_hash"] = signature

    # Note: Use requests or httpx to POST this to your Mendix endpoint
    return json.dumps(payload)