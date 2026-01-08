import os
import json
import hmac
import hashlib
import uuid
import requests
from datetime import datetime, timezone

def submit_prospect_to_mendix(prospect_data, analysis_data):
    """
    Called by Sentry once discovery is complete. 
    Matches the JSON structure of the discovery.html form.
    """
    # 1. Flatten the AI-extracted data for Mendix
    payload = {
        "source_system": "SENTRY-AI-AGENT",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contact_name": prospect_data.get("contact_name"),
        "company_name": prospect_data.get("company_name"),
        "bottleneck": prospect_data.get("bottleneck"),
        "sentry_notes": f"AI ANALYSIS: {analysis_data}"
    }

    # 2. HMAC-SHA256 Signing (matches your frontend logic)
    payload_string = json.dumps(payload, separators=(',', ':'))
    secret = os.getenv("MENDIX_HMAC_SECRET", "sei_systems_secure_gateway_01")
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 3. Dispatch to the Mendix endpoint
    # Note: Use the same URL your discovery.html uses
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
        if response.status_code in [200, 201]:
            return "SUCCESS: Strategic Roadmap Initialized in Mendix."
        else:
            return f"ERROR: Mendix Handshake Failed (Status {response.status_code})"
    except Exception as e:
        return f"CRITICAL: Gateway Connection Error: {str(e)}"