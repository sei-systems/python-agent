import os, json, hmac, hashlib, uuid, requests
from datetime import datetime, timezone

def submit_prospect_to_mendix(prospect_data, analysis_data):
    """
    Acts as Sentry's 'Salesman' closing the deal with a full data packet.
    """
    payload = {
        "source_system": "SENTRY-AI-AGENT",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contact_name": prospect_data.get("contact_name"),
        "company_name": prospect_data.get("company_name"),
        "employee_count": prospect_data.get("employee_count", "Unknown"),
        "bottleneck": prospect_data.get("bottleneck"),
        "tech_stack": prospect_data.get("tech_stack", "Not specified"),
        "sentry_notes": f"AI ANALYSIS: {analysis_data}"
    }

    # HMAC Signature
    payload_string = json.dumps(payload, separators=(',', ':'))
    secret = os.getenv("MENDIX_HMAC_SECRET", "sei_systems_secure_gateway_01")
    signature = hmac.new(secret.encode('utf-8'), payload_string.encode('utf-8'), hashlib.sha256).hexdigest()

    # Post to Mendix Production Gateway
    mendix_url = "https://crm315-sandbox.mxapps.io/rest/IncomingLead/v1/prospectiveLead"
    response = requests.post(mendix_url, json=payload, headers={"X-SEI-Signature": signature})
    return f"Success. Status: {response.status_code}"