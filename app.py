from flask import Flask, jsonify, request
import requests
import os
import tempfile

app = Flask(__name__)

cert_content = os.environ.get('CLIENT_CERT_CONTENT')
key_content = os.environ.get('CLIENT_KEY_CONTENT')

cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt')
cert_file.write(cert_content)
cert_file.close()

key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key')
key_file.write(key_content)
key_file.close()

CLIENT_CERT = (cert_file.name, key_file.name)
ING_TOKEN_URL = "https://api.sandbox.ing.com/oauth2/token"
ING_TRANSACTIONS_URL = "https://api.sandbox.ing.com/v1/accounts/{account_id}/transactions

@app.route("/get-token", methods=["GET"])
def get_token():
    data = {
        "grant_type": "client_credentials",
        "scope": "aispis"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    try:
        r = requests.post(
            ING_TOKEN_URL,
            data=data,
            headers=headers,
            cert=CLIENT_CERT,
            verify=True
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-transactions", methods=["GET"])
def get_transactions():
    account_id = request.args.get('account_id', 'YOUR_ACCOUNT_ID')
    
    token_response = requests.post(
        ING_TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "aispis"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        },
        cert=CLIENT_CERT,
        verify=True
    )
    
    if token_response.status_code != 200:
        return jsonify({"error": "Failed to get token", "details": token_response.text}), 500
    
    token = token_response.json().get("access_token")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    try:
        trans_response = requests.get(
            ING_TRANSACTIONS_URL.format(account_id=account_id),
            headers=headers,
            cert=CLIENT_CERT,
            verify=True
        )
        return jsonify(trans_response.json()), trans_response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
