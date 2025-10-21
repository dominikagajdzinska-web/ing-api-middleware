import os
import tempfile
import json
import base64
import subprocess
from flask import Flask, jsonify, request
import requests
from datetime import datetime, timezone

app = Flask(__name__)

TLS_CERT = ('certs/example_client_tls.cer', 'certs/example_client_tls.key')
SIGN_CERT = 'certs/example_client_signing.cer'
SIGN_KEY = 'certs/example_client_signing.key'

CLIENT_ID = '2cc378c2-0a8b-446a-b38e-ff6834398b4d'

ING_TOKEN_URL = "https://api.sandbox.ing.com/oauth2/token"
ING_ACCOUNTS_URL = "https://api.sandbox.ing.com/v1/accounts"
ING_TRANSACTIONS_URL = "https://api.sandbox.ing.com/v1/accounts/{account_id}/transactions"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

def create_jws(payload: str):
    fingerprint = subprocess.check_output(
        f"openssl x509 -noout -fingerprint -sha256 -inform pem -in {SIGN_CERT} | cut -d'=' -f2 | sed s/://g | xxd -r -p | base64 | tr -d '=' | tr '/+' '_-'",
        shell=True
    ).decode().strip()

    sigT = datetime.utcnow().replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    jws_header = {
        "b64": False,
        "x5t#S256": fingerprint,
        "crit": ["sigT", "sigD", "b64"],
        "sigT": sigT,
        "sigD": {
            "pars": ["(request-target)", "digest", "content-type"],
            "mId": "http://uri.etsi.org/19182/HttpHeaders"
        },
        "alg": "PS256"
    }

    jws_header_b64 = base64url_encode(json.dumps(jws_header).encode())

    digest = base64.b64encode(subprocess.check_output(
        f"echo -n '{payload}' | openssl dgst -binary -sha256", shell=True
    )).decode().rstrip('\n')

    signing_string = f"(request-target): post /oauth2/token\ndigest: SHA-256={digest}\ncontent-type: application/x-www-form-urlencoded"

    to_sign = f"{jws_header_b64}.{signing_string}"

    jws_signature = subprocess.check_output(
        f"echo -n \"{to_sign}\" | openssl dgst -sha256 -sign {SIGN_KEY} -sigopt rsa_padding_mode:pss | openssl base64 -A | tr -d '=' | tr '/+' '_-'",
        shell=True
    ).decode().strip()

    return f"{jws_header_b64}..{jws_signature}"

def get_access_token():
    payload = f"grant_type=client_credentials&scope=aispis&client_id={CLIENT_ID}"
    jws = create_jws(payload)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "x-jws-signature": jws,
        "TPP-Signature-Certificate": open(SIGN_CERT).read().replace("\n", "")
    }

    r = requests.post(ING_TOKEN_URL, data=payload, headers=headers, cert=TLS_CERT, verify=True)
    r.raise_for_status()
    return r.json().get("access_token")

@app.route("/accounts", methods=["GET"])
def get_accounts():
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        r = requests.get(ING_ACCOUNTS_URL, headers=headers, cert=TLS_CERT, verify=True)
        return jsonify(r.json()), r.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/transactions", methods=["GET"])
def get_transactions():
    account_id = request.args.get("account_id")
    if not account_id:
        return jsonify({"error": "account_id parameter is required"}), 400
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        r = requests.get(ING_TRANSACTIONS_URL.format(account_id=account_id), headers=headers, cert=TLS_CERT, verify=True)
        return jsonify(r.json()), r.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
