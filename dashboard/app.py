import os
import sys
from pathlib import Path

# Add project root to path so we can import from agents and database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from config import DASHBOARD_CONFIG
from database.db_manager import db
from database.models import TradeRecommendation, Asset, SentimentRecord, MarketData
from sqlalchemy import desc

app = Flask(__name__)
app.config['SECRET_KEY'] = DASHBOARD_CONFIG['secret_key']
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize DB connection for the app
session = db.get_session()

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/api/overview')
def api_overview():
    """Returns general market overview stats."""
    # This would normally pull from MarketData for indices.
    # We serve mock/placeholder data here if DB is empty for UI demonstration.
    try:
        latest_nifty = session.query(MarketData).filter(MarketData.ticker == '^NSEI').order_by(desc(MarketData.date)).first()
        nifty_price = latest_nifty.close if latest_nifty else 22500.00
        nifty_change = round((latest_nifty.close - latest_nifty.open) / latest_nifty.open * 100, 2) if latest_nifty else 1.25
        
        return jsonify({
            "status": "success",
            "indices": {
                "NIFTY_50": {"price": nifty_price, "change": nifty_change},
                "SENSEX": {"price": 74500.00, "change": 1.10},  # Mocked
                "BANK_NIFTY": {"price": 48200.00, "change": -0.45} # Mocked
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/recommendations')
def api_recommendations():
    """Returns recent AI recommendations."""
    try:
        recs = session.query(TradeRecommendation)\
            .order_by(desc(TradeRecommendation.timestamp))\
            .limit(10).all()
            
        data = []
        for r in recs:
            asset = session.query(Asset).filter(Asset.ticker == r.ticker).first()
            name = asset.name if asset else r.ticker

            data.append({
                "id": r.id,
                "ticker": r.ticker,
                "name": name,
                "time": r.timestamp.strftime("%Y-%m-%d %H:%M"),
                "strategy": r.strategy_type,
                "action": r.action,
                "entry": r.entry_price,
                "target": r.target_price_1,
                "stop": r.stop_loss,
                "confidence": round(r.confidence, 1),
                "reasoning": r.reasoning
            })
            
        # Add mock demo data if DB is empty to show the premium UI
        if not data:
            data = [
                {
                    "id": 1, "ticker": "RELIANCE.NS", "name": "Reliance Industries",
                    "time": "Just Now", "strategy": "Swing", "action": "BUY",
                    "entry": 2850.50, "target": 3050.00, "stop": 2750.00,
                    "confidence": 85.4, 
                    "reasoning": "ML: +7% Upside | TA: Golden Cross | News: Strong Q3 | R:R: 2.0"
                },
                 {
                    "id": 2, "ticker": "WIPRO.NS", "name": "Wipro Ltd",
                    "time": "15 mins ago", "strategy": "Intraday", "action": "SELL",
                    "entry": 450.20, "target": 435.00, "stop": 458.00,
                    "confidence": 72.1, 
                    "reasoning": "ML: -3% Downside | TA: RSI Overbought | News: Management Exit | R:R: 1.9"
                }
            ]

        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sentiment')
def api_sentiment():
    try:
        sentiments = session.query(SentimentRecord)\
            .order_by(desc(SentimentRecord.timestamp))\
            .limit(5).all()
            
        data = []
        for s in sentiments:
            data.append({
                "time": s.timestamp.strftime("%H:%M"),
                "source": s.source,
                "headline": s.headline,
                "label": s.sentiment_label,
                "score": round(s.sentiment_score * 100, 1) # As a percentage for UI
            })
            
        if not data:
            data = [
                {"time": "10:45", "source": "Bloomberg", "headline": "RBI keeps repo rate unchanged, markets surge.", "label": "POSITIVE", "score": 88.5},
                {"time": "10:12", "source": "Reuters", "headline": "IT sector struggles amid US economic data fears.", "label": "NEGATIVE", "score": -65.2},
                {"time": "09:30", "source": "Mint", "headline": "Adani Green announces 500MW solar project.", "label": "POSITIVE", "score": 75.0}
            ]
            
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start the Flask app
    # Use allow_unsafe_werkzeug=True purely for dev server with sockets
    socketio.run(app, host=DASHBOARD_CONFIG['host'], port=DASHBOARD_CONFIG['port'], debug=DASHBOARD_CONFIG['debug'], allow_unsafe_werkzeug=True)
