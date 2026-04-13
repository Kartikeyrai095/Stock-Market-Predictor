import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
socketio = SocketIO(app, cors_allowed_origins="*")

DATA_DIR  = Path(__file__).parent.parent / "data"
RECS_JSON = DATA_DIR / "recommendations.json"
SNAP_JSON = DATA_DIR / "market_snapshot.json"
STRAT_JSON = DATA_DIR / "strategies.json"

MF_DEMO = [
    {"id":"mf1","ticker":"MIRAE001","name":"Mirae Asset Large Cap","strategy":"SIP Opportunity","action":"BUY","entry":92.50,"target":105.00,"stop":85.00,"confidence":81.0,"reasoning":"ML: +13% upside over 12M | FinBERT: Positive FII inflow sentiment | Strong NAV momentum | R:R: 2.3","time":"Demo"},
    {"id":"mf2","ticker":"PPFC001","name":"Parag Parikh Flexi Cap","strategy":"Swing","action":"BUY","entry":68.10,"target":78.00,"stop":63.00,"confidence":76.4,"reasoning":"ML: +14% upside | Global diversification reduces risk | FinBERT: Neutral | Consistent alpha over Nifty | R:R: 2.0","time":"Demo"},
    {"id":"mf3","ticker":"AXIS001","name":"Axis Bluechip Fund","strategy":"Hold","action":"HOLD","entry":52.80,"target":60.00,"stop":48.00,"confidence":65.2,"reasoning":"ML: +14% upside | Underperformance due to insider issue resolved | Bottom accumulation phase | R:R: 1.8","time":"Demo"},
]
OPTIONS_DEMO = [
    {"id":"opt1","ticker":"NIFTY25500CE","name":"NIFTY 25500 CE (May)","strategy":"Options Buy","action":"BUY","entry":145.00,"target":320.00,"stop":70.00,"confidence":68.5,"reasoning":"ML: Bullish breakout above 25200 | Delta: 0.42 | IV: 14.2% (low) | Theta: -3.2 | Max Profit: ₹12,875 | Max Loss: ₹5,250","time":"Demo"},
    {"id":"opt2","ticker":"BANKNIFTY48500PE","name":"BANK NIFTY 48500 PE (May)","strategy":"Protective Put","action":"BUY","entry":185.00,"target":420.00,"stop":80.00,"confidence":72.1,"reasoning":"ML: Resistance at 49200 | Delta: -0.38 | IV: 16.8% | Theta: -5.1 | Hedge against long banking positions | R:R: 1.9","time":"Demo"},
]
INDICES_DEMO = [
    {"id":"idx1","ticker":"^NSEI","name":"NIFTY 50","strategy":"Index Trend","action":"BUY","entry":22450.00,"target":24000.00,"stop":21500.00,"confidence":74.3,"reasoning":"ML: Bullish | EMA 50 support intact | FII positive flows | FinBERT: 72% positive earnings season | R:R: 2.2","time":"Demo"},
    {"id":"idx2","ticker":"^NSEBANK","name":"NIFTY BANK","strategy":"Swing","action":"HOLD","entry":48100.00,"target":51000.00,"stop":46500.00,"confidence":61.5,"reasoning":"Mixed signals | Credit growth strong but NIM pressure | MACD crossover pending | Monitor for confirmation | R:R: 1.8","time":"Demo"},
]


def _load_json(path: Path, default):
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default


STOCKS_DEMO = [
    {"id":1,"ticker":"RELIANCE.NS","name":"Reliance Industries","time":"Demo Mode","strategy":"Swing","action":"BUY","entry":2850.50,"target":3050.00,"stop":2750.00,"confidence":85.4,"reasoning":"ML: +7% Upside | TA: Golden Cross | FinBERT: Positive Q3 Sentiment | R:R: 2.0"},
    {"id":2,"ticker":"WIPRO.NS","name":"Wipro Ltd","time":"Demo Mode","strategy":"Intraday","action":"SELL","entry":450.20,"target":435.00,"stop":458.00,"confidence":72.1,"reasoning":"ML: -3% Downside | TA: RSI Overbought (74) | FinBERT: Negative | R:R: 1.9"},
    {"id":3,"ticker":"HDFCBANK.NS","name":"HDFC Bank","time":"Demo Mode","strategy":"Swing","action":"BUY","entry":1620.00,"target":1750.00,"stop":1560.00,"confidence":78.9,"reasoning":"ML: +8% Upside | TA: EMA 50 Breakout | FinBERT: Strong Buy Signal | R:R: 2.2"},
    {"id":4,"ticker":"INFY.NS","name":"Infosys","time":"Demo Mode","strategy":"Swing","action":"BUY","entry":1780.00,"target":1920.00,"stop":1700.00,"confidence":70.3,"reasoning":"ML: +8% Upside | TA: Double Bottom Breakout | FinBERT: Positive IT sector sentiment | R:R: 1.75"},
    {"id":5,"ticker":"TCS.NS","name":"Tata Consultancy Services","time":"Demo Mode","strategy":"Positional","action":"HOLD","entry":4100.00,"target":4450.00,"stop":3900.00,"confidence":63.8,"reasoning":"ML: Neutral | TA: Consolidation phase | Awaiting quarterly results | R:R: 1.75"},
    {"id":6,"ticker":"BAJFINANCE.NS","name":"Bajaj Finance","time":"Demo Mode","strategy":"Swing","action":"BUY","entry":7200.00,"target":7800.00,"stop":6900.00,"confidence":80.1,"reasoning":"ML: +8% Upside | TA: RSI 62 with bullish divergence | Strong AUM growth | R:R: 2.0"},
    {"id":7,"ticker":"SUNPHARMA.NS","name":"Sun Pharma","time":"Demo Mode","strategy":"Positional","action":"BUY","entry":1650.00,"target":1850.00,"stop":1550.00,"confidence":74.6,"reasoning":"ML: +12% Upside | TA: Cup & Handle pattern | Specialty drug pipeline | FinBERT: Positive | R:R: 2.0"},
    {"id":8,"ticker":"SBIN.NS","name":"State Bank of India","time":"Demo Mode","strategy":"Swing","action":"SELL","entry":810.00,"target":765.00,"stop":835.00,"confidence":67.2,"reasoning":"ML: -5% Downside | TA: Head & Shoulders forming | NPA concerns | FinBERT: Neutral | R:R: 1.8"},
]

NEWS_DEMO = [
    {"time":"10:45","source":"Economic Times","headline":"RBI keeps repo rate unchanged at 6.5% — markets surge on liquidity relief measures.","label":"POSITIVE","score":88.5},
    {"time":"10:12","source":"LiveMint","headline":"IT sector struggles amid US economic data fears and global tariff risk escalation.","label":"NEGATIVE","score":-65.2},
    {"time":"09:30","source":"Moneycontrol","headline":"Adani Green announces major 500MW solar expansion project in Rajasthan.","label":"POSITIVE","score":75.0},
    {"time":"09:15","source":"Business Standard","headline":"FII inflows surge to ₹8,200 crore in April — third largest month in 2024.","label":"POSITIVE","score":82.0},
    {"time":"08:55","source":"NDTV Profit","headline":"Infosys revises guidance upward after strong Q4 results, beats estimates.","label":"POSITIVE","score":78.3},
    {"time":"08:30","source":"Reuters India","headline":"Crude oil prices dip 2% on demand concerns — positive for India import bill.","label":"POSITIVE","score":61.5},
    {"time":"08:00","source":"Bloomberg Quint","headline":"Banking sector faces NPA headwinds in Q4 — analysts cautious on PSU banks.","label":"NEGATIVE","score":-55.0},
    {"time":"07:45","source":"Financial Express","headline":"GST collections hit ₹1.96 lakh crore in March — near record high.","label":"POSITIVE","score":70.0},
    {"time":"07:30","source":"Moneycontrol","headline":"Pharma sector in focus as USFDA approval pipeline strengthens for 2025.","label":"NEUTRAL","score":45.0},
]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/overview')
def api_overview():
    snapshot = _load_json(SNAP_JSON, {})
    indices  = snapshot.get("indices", {})
    if not indices:
        indices = {
            "NIFTY_50":   {"price": 22500.00, "change": 0.00},
            "SENSEX":     {"price": 74100.00, "change": 0.00},
            "BANK_NIFTY": {"price": 48000.00, "change": 0.00},
        }
    return jsonify({"status": "success", "last_updated": snapshot.get("generated_at", "—"), "indices": indices})


@app.route('/api/recommendations')
def api_recommendations():
    asset_type = request.args.get('type', 'stocks')
    limit      = int(request.args.get('limit', 100))

    if asset_type == 'mutual_funds':
        return jsonify({"status": "success", "meta": {"run_mode": "demo"}, "data": MF_DEMO[:limit]})
    if asset_type == 'options':
        return jsonify({"status": "success", "meta": {"run_mode": "demo"}, "data": OPTIONS_DEMO[:limit]})
    if asset_type == 'indices':
        return jsonify({"status": "success", "meta": {"run_mode": "demo"}, "data": INDICES_DEMO[:limit]})

    # Stocks — prefer real data, fall back to demo
    payload = _load_json(RECS_JSON, {})
    recs    = payload.get("recommendations", [])
    data = []
    for item in recs:
        r = item.get("result", item)
        data.append({
            "id": r.get("id", len(data)+1), "ticker": r.get("ticker", item.get("ticker","—")),
            "name": r.get("name", r.get("ticker","—")), "time": item.get("timestamp", "—"),
            "strategy": r.get("strategy_type", r.get("strategy","Swing")),
            "action": r.get("action","BUY"), "entry": r.get("entry_price", r.get("entry",0)),
            "target": r.get("target_price_1", r.get("target",0)), "stop": r.get("stop_loss", r.get("stop",0)),
            "confidence": round(float(r.get("confidence",0)),1), "reasoning": r.get("reasoning",""),
        })

    if not data:
        data = STOCKS_DEMO

    return jsonify({"status": "success", "meta": {"run_at": payload.get("run_at","—"), "run_mode": payload.get("run_mode","demo")}, "data": data[:limit]})


@app.route('/api/sentiment')
def api_sentiment():
    payload   = _load_json(RECS_JSON, {})
    headlines = payload.get("headlines", [])
    return jsonify({"status": "success", "data": headlines or NEWS_DEMO})


@app.route('/api/strategies')
def api_strategies():
    payload = _load_json(STRAT_JSON, {})
    data    = payload.get("strategies", [])
    return jsonify({"status": "success", "data": data})


@app.route('/api/system_status')
def api_system_status():
    payload = _load_json(RECS_JSON, {})
    return jsonify({
        "status":      "success",
        "last_run_at": payload.get("run_at", "Never"),
        "run_mode":    payload.get("run_mode", "unknown"),
        "ai_engine":   "GitHub Actions (Free Cloud)",
        "dashboard":   "Render.com (Free Cloud)",
    })


if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
