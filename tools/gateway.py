import os
import json
import hmac
import hashlib
import uuid
import requests
from datetime import datetime, timezone

def submit_prospect_to_mendix(prospect_data, analysis_data):
    """
    Formulates a JSON payload identical to the web form
    and signs it for the Mendix Production Gateway.
    """
    # 1. Align payload with the flattened Mendix Entity structure
    payload = {
        "source_system": "SENTRY-AI-AGENT",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contact_name": prospect_data.get("contact_name"),
        "company_name": prospect_data.get("company_name"),
        "bottleneck": prospect_data.get("bottleneck"),
        "sentry_notes": f"AI ANALYSIS: {analysis_data}"
    }

    # 2. Strict HMAC Generation (SOC 2 Alignment)
    # separators=(',', ':') removes whitespace to ensure hash matches Javascript's stringify
    payload_string = json.dumps(payload, separators=(',', ':'))
    
    secret = os.getenv("MENDIX_HMAC_SECRET", "sei_systems_secure_gateway_01")
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 3. Post to the standard Mendix REST endpoint
    mendix_url = "https://crm315-sandbox.mxapps.io/rest/IncomingLead/v1/prospectiveLead"
    
    try:
        response = requests.post(
            mendix_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-SEI-Signature": signature
            },
            timeout=10
        )
        if response.status_code == 200 or response.status_code == 201:
            return "Strategic Roadmap Initialized. Our team will be in touch."
        else:
            return f"Transmission Handshake Failed (Error {response.status_code})"
    except Exception as e:
        return f"Gateway Connection Offline: {str(e)}"