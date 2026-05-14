import os
import hmac
import hashlib
import json
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "SKYCONET_HBAR_2024")

BYBIT_BASE_URL = "https://api.bybit.com"
SYMBOL = "HBARUSDT"
ORDER_QTY = "100"

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "SKYCONET HBAR Bot online"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    if data.get("secret", "") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    action = data.get("action", "").upper()
    if action not in ("BUY", "SELL"):
        return jsonify({"error": f"Invalid action: {action}"}), 400
    side = "Buy" if action == "BUY" else "Sell"
    result = place_order(side, ORDER_QTY)
    return jsonify(result), 200

def place_order(side, qty):
    endpoint = "/v5/order/create"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    body = {
        "category": "spot",
        "symbol": SYMBOL,
        "side": side,
        "orderType": "Market",
        "qty": qty,
    }
    body_str = json.dumps(body, separators=(',', ':'))
    param_str = timestamp + BYBIT_API_KEY + recv_window + body_str
    signature = hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            BYBIT_BASE_URL + endpoint,
            data=body_str,
            headers=headers,
            timeout=10
        )
        resp_json = resp.json()
        return {
            "order_side": side,
            "symbol": SYMBOL,
            "qty": qty,
            "bybit_retCode": resp_json.get("retCode"),
            "bybit_retMsg": resp_json.get("retMsg"),
            "orderId": resp_json.get("result", {}).get("orderId", ""),
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
