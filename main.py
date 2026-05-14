from flask import Flask, request, jsonify
import hashlib
import hmac
import time
import requests
import json
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "SKYCONET_HBAR_2024")
BASE_URL         = "https://api.bybit.com"
SYMBOL           = "HBARUSDT"

def bybit_post(endpoint, body):
    timestamp = str(int(time.time() * 1000))
    body_str  = json.dumps(body)
    payload   = f"{timestamp}{BYBIT_API_KEY}5000{body_str}"
    signature = hmac.new(BYBIT_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": "5000",
        "Content-Type": "application/json"
    }
    response = requests.post(BASE_URL + endpoint, headers=headers, data=body_str)
    return response.json()

def get_balance():
    timestamp = str(int(time.time() * 1000))
    params = "accountType=SPOT"
    payload = f"{timestamp}{BYBIT_API_KEY}5000{params}"
    signature = hmac.new(BYBIT_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": "5000"
    }
    response = requests.get(f"{BASE_URL}/v5/account/wallet-balance?accountType=SPOT", headers=headers)
    data = response.json()
    try:
        coins = data["result"]["list"][0]["coin"]
        for coin in coins:
            if coin["coin"] == "USDT":
                return float(coin["walletBalance"])
    except:
        pass
    return 0.0

def place_order(side, usdt_amount):
    price_resp = requests.get(f"{BASE_URL}/v5/market/tickers?category=spot&symbol={SYMBOL}")
    price_data = price_resp.json()
    price = float(price_data["result"]["list"][0]["lastPrice"])
    qty = round(usdt_amount / price, 0)
    body = {
        "category": "spot",
        "symbol": SYMBOL,
        "side": side,
        "orderType": "Market",
        "qty": str(int(qty))
    }
    return bybit_post("/v5/order/create", body)

@app.route("/webhook", methods=["POST"])
def webhook():
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    action = data.get("action", "").upper()
    logging.info(f"Signal received: {action}")
    if action == "BUY":
        balance = get_balance()
        if balance < 10:
            return jsonify({"error": "Insufficient balance"}), 400
        result = place_order("Buy", balance * 0.95)
        logging.info(f"BUY order: {result}")
        return jsonify({"status": "BUY executed", "result": result})
    elif action == "SELL":
        timestamp = str(int(time.time() * 1000))
        params = "accountType=SPOT"
        payload = f"{timestamp}{BYBIT_API_KEY}5000{params}"
        signature = hmac.new(BYBIT_API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": BYBIT_API_KEY,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": "5000"
        }
        resp = requests.get(f"{BASE_URL}/v5/account/wallet-balance?accountType=SPOT", headers=headers)
        hbar_qty = 0
        try:
            coins = resp.json()["result"]["list"][0]["coin"]
            for coin in coins:
                if coin["coin"] == "HBAR":
                    hbar_qty = float(coin["walletBalance"])
        except:
            pass
        if hbar_qty < 1:
            return jsonify({"error": "No HBAR to sell"}), 400
        body = {
            "category": "spot",
            "symbol": SYMBOL,
            "side": "Sell",
            "orderType": "Market",
            "qty": str(int(hbar_qty * 0.95))
        }
        result = bybit_post("/v5/order/create", body)
        logging.info(f"SELL order: {result}")
        return jsonify({"status": "SELL executed", "result": result})
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "SKYCONET HBAR Bot running", "symbol": SYMBOL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)