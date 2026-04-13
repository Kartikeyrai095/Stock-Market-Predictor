"""
Central Configuration for Indian Stock Market Multi-Agent AI System
All constants, tickers, and settings are managed here.
"""

import os
from pathlib import Path
from datetime import time

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = DATA_DIR / "models"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "market.db"

# Create directories if they don't exist
for d in [DATA_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
#  MARKET SETTINGS
# ─────────────────────────────────────────────
MARKET_OPEN = time(9, 15)    # 9:15 AM IST
MARKET_CLOSE = time(15, 30)  # 3:30 PM IST
TIMEZONE = "Asia/Kolkata"

# Refresh intervals
INTRADAY_REFRESH_SECONDS = 300   # 5 minutes during market hours
AFTER_HOURS_REFRESH_SECONDS = 3600  # 1 hour after hours
NEWS_REFRESH_SECONDS = 600       # 10 minutes

# ─────────────────────────────────────────────
#  STOCK UNIVERSE
# ─────────────────────────────────────────────

NIFTY_50 = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
    "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
    "BPCL.NS", "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS",
    "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS",
    "KOTAKBANK.NS", "LTIM.NS", "LT.NS", "M&M.NS",
    "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS",
    "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS", "TITAN.NS",
    "ULTRACEMCO.NS", "WIPRO.NS",
]

NIFTY_NEXT_50 = [
    "ABB.NS", "ADANIENSOL.NS", "ADANIPOWER.NS", "AMBUJACEM.NS",
    "DMART.NS", "BANKBARODA.NS", "BERGEPAINT.NS", "BEL.NS",
    "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS", "COLPAL.NS",
    "DABUR.NS", "DLF.NS", "GAIL.NS", "GODREJCP.NS",
    "HAVELLS.NS", "HAL.NS", "ICICIPRULI.NS", "IOC.NS",
    "INDHOTEL.NS", "INDUSTOWER.NS", "IRCTC.NS", "JINDALSTEL.NS",
    "JUBLFOOD.NS", "LICI.NS", "LUPIN.NS", "MARICO.NS",
    "MCDOWELL-N.NS", "MUTHOOTFIN.NS", "NAUKRI.NS", "NHPC.NS",
    "NMDC.NS", "OFSS.NS", "PIIND.NS", "PFC.NS",
    "PIDILITIND.NS", "PNB.NS", "RECLTD.NS", "SAIL.NS",
    "SHREECEM.NS", "SIEMENS.NS", "SOLARINDS.NS", "TORNTPHARM.NS",
    "TRENT.NS", "TVSMOTOR.NS", "UNIONBANK.NS", "VBL.NS",
    "VEDL.NS", "ZOMATO.NS",
]

NIFTY_MIDCAP_100_SAMPLE = [
    "AUROPHARMA.NS", "BALKRISIND.NS", "BATAINDIA.NS", "BHARATFORG.NS",
    "CROMPTON.NS", "CYIENT.NS", "ESCORTS.NS", "EXIDEIND.NS",
    "FEDERALBNK.NS", "GMRINFRA.NS", "GODREJPROP.NS", "GUJGASLTD.NS",
    "ICICIGI.NS", "IDFCFIRSTB.NS", "INDIANHOTEL.NS", "INDRAPRASTHA.NS",
    "JKCEMENT.NS", "JUBILANTFOODWORKS.NS", "KANSAINER.NS", "LTF.NS",
    "LTTS.NS", "MAXHEALTH.NS", "MCX.NS", "METROPOLIS.NS",
    "MGL.NS", "MOTHERSON.NS", "MPHASIS.NS", "NAUKRI.NS",
    "PAGEIND.NS", "PERSISTENT.NS", "PETRONET.NS", "PHOENIXLTD.NS",
    "POLYCAB.NS", "RBLBANK.NS", "SYNGENE.NS", "TATACOMM.NS",
    "TATAELXSI.NS", "TATAINVEST.NS", "TORNTPOWER.NS", "VOLTAS.NS",
]

# NSE Indices (for reference data)
INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY REALTY": "^CNXREALTY",
}

# All tracked universe
ALL_STOCKS = list(set(NIFTY_50 + NIFTY_NEXT_50 + NIFTY_MIDCAP_100_SAMPLE))

# ─────────────────────────────────────────────
#  NEWS SOURCES — RSS FEEDS (Free)
# ─────────────────────────────────────────────
NEWS_RSS_FEEDS = {
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rss.cms",
    "Economic Times Stocks": "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "LiveMint Markets": "https://www.livemint.com/rss/markets",
    "Business Standard Markets": "https://www.business-standard.com/rss/markets-106.rss",
    "NDTV Profit": "https://feeds.feedburner.com/ndtvprofit-latest",
    "Financial Express Markets": "https://www.financialexpress.com/market/feed/",
    "Reuters India Business": "https://feeds.reuters.com/reuters/INbusinessNews",
    "Bloomberg Quint": "https://www.bqprime.com/rss",
}

# ─────────────────────────────────────────────
#  ML MODEL SETTINGS
# ─────────────────────────────────────────────

LSTM_CONFIG = {
    "lookback_days": 60,          # Days of history as input
    "forecast_days": 5,           # Days to predict ahead
    "lstm_units": [128, 64],      # Units per LSTM layer
    "dropout_rate": 0.2,
    "batch_size": 32,
    "epochs": 100,
    "patience": 15,               # Early stopping patience
    "learning_rate": 0.001,
    "features": [                 # Feature columns used
        "Open", "High", "Low", "Close", "Volume",
        "RSI", "MACD", "MACD_signal", "MACD_hist",
        "BB_upper", "BB_middle", "BB_lower",
        "EMA_9", "EMA_21", "EMA_50", "EMA_200",
        "ATR", "ADX", "Stoch_K", "Stoch_D",
        "OBV", "CCI", "Williams_R", "MFI",
        "ROC", "VWAP",
    ],
}

TRANSFORMER_CONFIG = {
    "lookback_days": 60,
    "forecast_days": 5,
    "d_model": 64,
    "num_heads": 4,
    "num_encoder_layers": 2,
    "dff": 128,
    "dropout_rate": 0.1,
    "batch_size": 32,
    "epochs": 80,
    "patience": 12,
    "learning_rate": 0.0005,
}

RL_CONFIG = {
    "algorithm": "PPO",           # PPO or DQN
    "total_timesteps": 100_000,
    "learning_rate": 0.0003,
    "initial_capital": 1_000_000,  # ₹10,00,000 (virtual)
    "transaction_cost": 0.001,     # 0.1% per trade
    "reward_scaling": 1e-4,
}

# ─────────────────────────────────────────────
#  BACKTESTING
# ─────────────────────────────────────────────
BACKTEST_CONFIG = {
    "initial_capital": 1_000_000,   # ₹10,00,000 virtual
    "transaction_cost_pct": 0.001,  # 0.1% brokerage
    "slippage_pct": 0.0005,         # 0.05% slippage
    "start_date": "2018-01-01",
    "benchmark": "^NSEI",           # NIFTY 50
    "walk_forward_months": 6,
}

# ─────────────────────────────────────────────
#  RISK MANAGEMENT
# ─────────────────────────────────────────────
RISK_CONFIG = {
    "max_position_pct": 0.05,       # Max 5% per trade
    "max_sector_exposure_pct": 0.20, # Max 20% per sector
    "max_total_exposure_pct": 0.50,  # Max 50% total exposure
    "min_risk_reward_ratio": 2.0,    # Minimum 1:2 R:R
    "min_confidence_pct": 60.0,      # Min 60% confidence
    "max_correlation": 0.70,         # Max correlation with existing positions
    "var_confidence_level": 0.95,    # 95% VaR
    "max_drawdown_pct": 0.20,        # 20% max drawdown circuit breaker
}

# ─────────────────────────────────────────────
#  RECOMMENDATION AGENT WEIGHTS
# ─────────────────────────────────────────────
RECOMMENDATION_WEIGHTS = {
    "prediction_confidence": 0.30,
    "backtest_performance": 0.25,
    "technical_setup": 0.20,
    "sentiment_score": 0.15,
    "risk_score": 0.10,
}

# ─────────────────────────────────────────────
#  SELF-LEARNING THRESHOLDS
# ─────────────────────────────────────────────
LEARNING_CONFIG = {
    "retrain_accuracy_threshold": 0.55,  # Retrain if accuracy < 55%
    "min_samples_for_retrain": 30,
    "weight_adjustment_rate": 0.05,
    "performance_window_days": 30,
}

# ─────────────────────────────────────────────
#  SCHEDULING (APScheduler)
# ─────────────────────────────────────────────
SCHEDULE_CONFIG = {
    "market_data_refresh": "*/5 9-15 * * 1-5",      # Every 5 min, Mon-Fri, 9-15h
    "news_refresh": "*/10 * * * *",                   # Every 10 min
    "daily_analysis": "0 16 * * 1-5",                # 4 PM weekdays
    "weekly_retrain": "0 8 * * 6",                    # 8 AM Saturdays
    "prediction_score": "30 16 * * 1-5",              # 4:30 PM weekdays
}

# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
DASHBOARD_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": True,
    "secret_key": os.urandom(24).hex(),
    "auto_refresh_seconds": 60,
}

# ─────────────────────────────────────────────
#  ML MODEL: NLP / SENTIMENT
# ─────────────────────────────────────────────
SENTIMENT_CONFIG = {
    "model_name": "ProsusAI/finbert",
    "max_sequence_length": 512,
    "batch_size": 8,
    "sentiment_decay_hours": 24,  # News older than 24h gets lower weight
}

# ─────────────────────────────────────────────
#  OPTIONS SETTINGS
# ─────────────────────────────────────────────
OPTIONS_CONFIG = {
    "expiry_preference": "near",   # near or next
    "min_oi": 100,                  # Minimum open interest
    "min_iv_rank": 20,              # IV Rank threshold
    "max_iv_rank": 80,
    "greeks": ["delta", "gamma", "theta", "vega", "rho"],
    "strategies": [
        "long_call", "long_put",
        "bull_call_spread", "bear_put_spread",
        "iron_condor", "iron_butterfly",
        "covered_call", "protective_put",
        "straddle", "strangle",
    ],
}

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
}
