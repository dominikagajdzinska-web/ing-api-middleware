import os
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

TLS_CERT = ('certs/example_client_tls.cer', 'certs/example_client_tls.key')
SIGN_CERT = ('certs/example_client_signing.cer', 'certs/example_client_signing.key')

CLIENT_ID = os.environ.get('ING_CLIENT_ID', '2cc378c2-0a8b-446a-b38e-ff6834398b4d')

ING_TOKEN_URL = "https://api.sandbox.ing.com/oauth2/token"
ING_ACCOUNTS_URL = "https://api.sandbox.ing.com/v1/accounts"
ING_TRANSACTIONS_URL = "https://api.sandbox.ing.com/v1/accounts/{account_id}/transactions"


def get_access_token():
    data = {
        "grant_type": "client_credentials",
        "scope": "aispis",
        "client_id": CLIENT_ID
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    r = requests.post(ING_TOKEN_URL, data=data, headers=headers, cert=TLS_CERT, verify=True)
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
        r = requests.get(ING_TRANSACTIONS_URL.format(account_id=account_id),
                         headers=headers, cert=TLS_CERT, verify=True)
        return jsonify(r.json()), r.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
