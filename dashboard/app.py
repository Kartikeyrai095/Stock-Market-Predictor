import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
socketio = SocketIO(app, cors_allowed_origins="*")

# ─── Data source helpers ───
DATA_DIR = Path(__file__).parent.parent / "data"
RECS_JSON = DATA_DIR / "recommendations.json"
MARKET_JSON = DATA_DIR / "market_snapshot.json"


def _load_json(path: Path, default):
    """Safely load a JSON file, returning default on any error."""
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default


# ─── Routes ───

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/overview')
def api_overview():
    """Market index overview — loaded from market_snapshot.json written by GitHub Actions."""
    snapshot = _load_json(MARKET_JSON, {})
    indices = snapshot.get("indices", {})

    # Fall back to hard-coded placeholders if no data yet
    if not indices:
        indices = {
            "NIFTY_50":   {"price": 22500.00, "change": 0.00},
            "SENSEX":     {"price": 74100.00, "change": 0.00},
            "BANK_NIFTY": {"price": 48000.00, "change": 0.00},
        }

    return jsonify({
        "status": "success",
        "last_updated": snapshot.get("generated_at", "—"),
        "indices": indices,
    })


@app.route('/api/recommendations')
def api_recommendations():
    """AI trade recommendations — from recommendations.json committed by GitHub Actions."""
    payload = _load_json(RECS_JSON, {})
    recs = payload.get("recommendations", [])

    # Flatten the nested structure written by ci_runner.py
    data = []
    for item in recs:
        r = item.get("result", item)
        data.append({
            "id":         r.get("id", len(data) + 1),
            "ticker":     r.get("ticker", item.get("ticker", "—")),
            "name":       r.get("name", r.get("ticker", "—")),
            "time":       item.get("timestamp", r.get("time", "—")),
            "strategy":   r.get("strategy_type", r.get("strategy", "—")),
            "action":     r.get("action", "—"),
            "entry":      r.get("entry_price", r.get("entry", 0)),
            "target":     r.get("target_price_1", r.get("target", 0)),
            "stop":       r.get("stop_loss", r.get("stop", 0)),
            "confidence": round(float(r.get("confidence", 0)), 1),
            "reasoning":  r.get("reasoning", ""),
        })

    # ─── Always populate with demo data if empty so UI looks great ───
    if not data:
        data = [
            {
                "id": 1, "ticker": "RELIANCE.NS", "name": "Reliance Industries",
                "time": "Demo Mode", "strategy": "Swing", "action": "BUY",
                "entry": 2850.50, "target": 3050.00, "stop": 2750.00,
                "confidence": 85.4,
                "reasoning": "ML: +7% Upside | TA: Golden Cross | FinBERT: Positive Q3 Sentiment | R:R: 2.0"
            },
            {
                "id": 2, "ticker": "WIPRO.NS", "name": "Wipro Ltd",
                "time": "Demo Mode", "strategy": "Intraday", "action": "SELL",
                "entry": 450.20, "target": 435.00, "stop": 458.00,
                "confidence": 72.1,
                "reasoning": "ML: -3% Downside | TA: RSI Overbought (74) | FinBERT: Negative | R:R: 1.9"
            },
            {
                "id": 3, "ticker": "HDFCBANK.NS", "name": "HDFC Bank",
                "time": "Demo Mode", "strategy": "Swing", "action": "BUY",
                "entry": 1620.00, "target": 1750.00, "stop": 1560.00,
                "confidence": 78.9,
                "reasoning": "ML: +8% Upside | TA: EMA 50 Breakout | FinBERT: Strong Buy Signal | R:R: 2.2"
            },
        ]

    meta = {
        "run_at": payload.get("run_at", "—"),
        "run_mode": payload.get("run_mode", "demo"),
        "count": payload.get("count", len(data)),
    }

    return jsonify({"status": "success", "meta": meta, "data": data})


@app.route('/api/sentiment')
def api_sentiment():
    """News sentiment — from recommendations.json or static demo."""
    payload = _load_json(RECS_JSON, {})
    headlines = payload.get("headlines", [])

    if not headlines:
        headlines = [
            {"time": "10:45", "source": "Economic Times", "headline": "RBI keeps repo rate unchanged — markets surge on liquidity relief.", "label": "POSITIVE", "score": 88.5},
            {"time": "10:12", "source": "LiveMint",        "headline": "IT sector struggles amid US economic data fears and tariff risks.", "label": "NEGATIVE", "score": -65.2},
            {"time": "09:30", "source": "Moneycontrol",    "headline": "Adani Green announces 500MW solar expansion project.", "label": "POSITIVE", "score": 75.0},
        ]

    return jsonify({"status": "success", "data": headlines})


@app.route('/api/system_status')
def api_system_status():
    """Returns when the AI engine last ran."""
    payload = _load_json(RECS_JSON, {})
    return jsonify({
        "status":      "success",
        "last_run_at": payload.get("run_at", "Never"),
        "run_mode":    payload.get("run_mode", "unknown"),
        "ai_engine":   "GitHub Actions (Free Cloud)",
        "dashboard":   "Render.com (Free Cloud)",
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
