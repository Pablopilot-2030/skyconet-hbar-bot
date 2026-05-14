import os
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Config desde variables de entorno ──────────────────────────────────────
BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET", "")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "SKYCONET_HBAR_2024")

BYBIT_BASE_URL   = "https://api.bybit.com"
SYMBOL           = "HBARUSDT"
ORDER_QTY        = "100"   # unidades HBAR por orden — ajustar según capital

# ── Health check ───────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "SKYCONET HBAR Bot online"}), 200

# ── Webhook principal ───────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    # Verificar secret en el body
    secret = data.get("secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    action = data.get("action", "").upper()   # "BUY" o "SELL"
    price  = data.get("price", "market")

    if action not in ("BUY", "SELL"):
        return jsonify({"error": f"Invalid action: {action}"}), 400

    side = "Buy" if action == "BUY" else "Sell"

    result = place_order(side, ORDER_QTY)
    return jsonify(result), 200

# ── Bybit order ─────────────────────────────────────────────────────────────
def bybit_signature(params: dict, secret: str, timestamp: str, recv_window: str) -> str:
    param_str = timestamp + BYBIT_API_KEY + recv_window + dict_to_query(params)
    return hmac.new(secret.encode("utf-8"),
                    param_str.encode("utf-8"),
                    hashlib.sha256).hexdigest()

def dict_to_query(params: dict) -> str:
    return "&".join(f"{k}={v}" for k, v in sorted(params.items()))

def place_order(side: str, qty: str) -> dict:
    endpoint  = "/v5/order/create"
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    body = {
        "category":   "spot",
        "symbol":     SYMBOL,
        "side":       side,
        "orderType":  "Market",
        "qty":        qty,
    }

    signature = bybit_signature(body, BYBIT_API_SECRET, timestamp, recv_window)

    headers = {
        "X-BAPI-API-KEY":     BYBIT_API_KEY,
        "X-BAPI-SIGN":        signature,
        "X-BAPI-TIMESTAMP":   timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type":       "application/json",
    }

    try:
        resp = requests.post(
            BYBIT_BASE_URL + endpoint,
            json=body,
            headers=headers,
            timeout=10
        )
        resp_json = resp.json()
        return {
            "order_side":   side,
            "symbol":       SYMBOL,
            "qty":          qty,
            "bybit_retCode": resp_json.get("retCode"),
            "bybit_retMsg":  resp_json.get("retMsg"),
            "orderId":       resp_json.get("result", {}).get("orderId", ""),
        }
    except Exception as e:
        return {"error": str(e)}

# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
