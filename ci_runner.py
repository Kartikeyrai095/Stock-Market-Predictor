"""
ci_runner.py — GitHub Actions Entry Point
Generates real recommendations from first run onwards using a direct yfinance
path that bypasses the SQLite dependency. The full multi-agent pipeline also
runs and its results override these if available.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger

logger = get_logger("CI_Runner")


# ─────────────────────────────────────────────────────────────────────────────
# Market Snapshot (index prices)
# ─────────────────────────────────────────────────────────────────────────────

def _export_market_snapshot():
    try:
        import yfinance as yf
        index_map = {"^NSEI": "NIFTY_50", "^BSESN": "SENSEX", "^NSEBANK": "BANK_NIFTY"}
        result = {}
        for symbol, name in index_map.items():
            try:
                hist = yf.Ticker(symbol).history(period="2d")
                if len(hist) >= 2:
                    today = float(hist["Close"].iloc[-1])
                    prev  = float(hist["Close"].iloc[-2])
                    result[name] = {
                        "price":  round(today, 2),
                        "change": round((today - prev) / prev * 100, 2),
                    }
            except Exception as e:
                logger.warning(f"  Index {symbol} failed: {e}")

        os.makedirs("data", exist_ok=True)
        with open("data/market_snapshot.json", "w") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "indices": result}, f, indent=2)
        logger.info("✅ market_snapshot.json written")
    except Exception as e:
        logger.warning(f"Market snapshot skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Direct TA-based Recommendation Builder (no SQLite, no ML needed)
# Runs on every invocation to guarantee at least N recommendations
# ─────────────────────────────────────────────────────────────────────────────

def _direct_ta_recommendations(tickers: list) -> list:
    """
    Fetch 6 months of OHLCV data from yfinance for each ticker,
    compute key indicators inline, and produce a BUY/SELL/HOLD call
    with entry, target, stop-loss, and reasoning.  No SQLite required.
    """
    try:
        import yfinance as yf
        import pandas as pd
        import numpy as np
    except ImportError as e:
        logger.error(f"Missing dependency for direct TA: {e}")
        return []

    recommendations = []

    COMPANY_NAMES = {
        "RELIANCE.NS": "Reliance Industries",  "TCS.NS": "Tata Consultancy Services",
        "HDFCBANK.NS": "HDFC Bank",            "INFY.NS": "Infosys",
        "ICICIBANK.NS": "ICICI Bank",          "BAJFINANCE.NS": "Bajaj Finance",
        "AXISBANK.NS": "Axis Bank",            "WIPRO.NS": "Wipro",
        "LT.NS": "Larsen & Toubro",            "MARUTI.NS": "Maruti Suzuki",
        "SUNPHARMA.NS": "Sun Pharmaceutical",  "SBIN.NS": "State Bank of India",
        "TATAMOTORS.NS": "Tata Motors",        "HINDUNILVR.NS": "Hindustan Unilever",
        "KOTAKBANK.NS": "Kotak Mahindra Bank", "NTPC.NS": "NTPC",
        "ADANIENT.NS": "Adani Enterprises",    "ONGC.NS": "ONGC",
        "POWERGRID.NS": "Power Grid Corporation",
    }

    for ticker in tickers:
        try:
            logger.info(f"  Direct TA → {ticker}")
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if df is None or len(df) < 60:
                logger.warning(f"  Insufficient data for {ticker}")
                continue

            close  = df["Close"].squeeze()
            high   = df["High"].squeeze()
            low    = df["Low"].squeeze()
            volume = df["Volume"].squeeze()

            # ── Indicators ──
            ema_9   = close.ewm(span=9,   adjust=False).mean()
            ema_21  = close.ewm(span=21,  adjust=False).mean()
            ema_50  = close.ewm(span=50,  adjust=False).mean()
            ema_200 = close.ewm(span=200, adjust=False).mean()

            # RSI
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi   = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

            # MACD
            macd_line   = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
            macd_signal = macd_line.ewm(span=9, adjust=False).mean()

            # Bollinger Bands
            bb_mid   = close.rolling(20).mean()
            bb_std   = close.rolling(20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std

            # ATR
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            # Volume SMA
            vol_sma = volume.rolling(20).mean()

            # Latest values
            price     = float(close.iloc[-1])
            rsi_now   = float(rsi.iloc[-1])
            macd_now  = float(macd_line.iloc[-1])
            macd_sig  = float(macd_signal.iloc[-1])
            ema9_now  = float(ema_9.iloc[-1])
            ema21_now = float(ema_21.iloc[-1])
            ema50_now = float(ema_50.iloc[-1])
            ema200_now= float(ema_200.iloc[-1])
            atr_now   = float(atr.iloc[-1])
            bb_u      = float(bb_upper.iloc[-1])
            bb_l      = float(bb_lower.iloc[-1])
            vol_now   = float(volume.iloc[-1])
            vol_avg   = float(vol_sma.iloc[-1])

            # ── Scoring ──
            score = 0
            signals = []

            # Trend signals
            if ema9_now > ema21_now > ema50_now:
                score += 2; signals.append("EMA 9>21>50 Bullish Alignment")
            elif ema9_now < ema21_now < ema50_now:
                score -= 2; signals.append("EMA 9<21<50 Bearish Alignment")

            if price > ema200_now:
                score += 1; signals.append("Above EMA 200 (Long-term Uptrend)")
            else:
                score -= 1; signals.append("Below EMA 200 (Long-term Downtrend)")

            # Golden/Death Cross
            if ema21_now > ema50_now and float(ema_21.iloc[-2]) <= float(ema_50.iloc[-2]):
                score += 2; signals.append("🟢 Golden Cross (EMA 21 crossed EMA 50)")
            elif ema21_now < ema50_now and float(ema_21.iloc[-2]) >= float(ema_50.iloc[-2]):
                score -= 2; signals.append("🔴 Death Cross (EMA 21 crossed below EMA 50)")

            # RSI
            if rsi_now < 35:
                score += 1; signals.append(f"RSI Oversold ({rsi_now:.0f}) — potential reversal")
            elif rsi_now > 70:
                score -= 1; signals.append(f"RSI Overbought ({rsi_now:.0f}) — caution")
            else:
                signals.append(f"RSI Neutral ({rsi_now:.0f})")

            # MACD
            if macd_now > macd_sig and float(macd_line.iloc[-2]) <= float(macd_signal.iloc[-2]):
                score += 1; signals.append("MACD Bullish Crossover")
            elif macd_now < macd_sig and float(macd_line.iloc[-2]) >= float(macd_signal.iloc[-2]):
                score -= 1; signals.append("MACD Bearish Crossover")

            # Bollinger squeeze/breakout
            if price > bb_u:
                score -= 1; signals.append("Price above Upper BB — extended")
            elif price < bb_l:
                score += 1; signals.append("Price below Lower BB — potential bounce")

            # Volume confirmation
            if vol_now > vol_avg * 1.5:
                vol_tag = "High volume confirms move"
                score = score + 1 if score > 0 else score - 1
                signals.append(vol_tag)

            # ── Decision ──
            max_score = 9
            confidence = min(95, max(45, 50 + (score / max_score) * 45))

            if score >= 2:
                action = "BUY"
                target = round(price + 2.0 * atr_now, 2)
                stop   = round(price - 1.0 * atr_now, 2)
                strategy = "Swing" if abs(score) < 4 else "Positional"
            elif score <= -2:
                action = "SELL"
                target = round(price - 2.0 * atr_now, 2)
                stop   = round(price + 1.0 * atr_now, 2)
                strategy = "Swing"
            else:
                action = "HOLD"
                target = round(price + 1.5 * atr_now, 2)
                stop   = round(price - 1.0 * atr_now, 2)
                strategy = "Positional"
                confidence = max(45, confidence - 10)

            rr = abs(target - price) / max(abs(price - stop), 0.01)
            reasoning = " | ".join(signals[:4]) + f" | R:R {rr:.1f} | ATR ₹{atr_now:.1f}"

            recommendations.append({
                "ticker":     ticker,
                "result": {
                    "ticker":     ticker,
                    "name":       COMPANY_NAMES.get(ticker, ticker.replace(".NS", "")),
                    "action":     action,
                    "strategy":   strategy,
                    "entry":      round(price, 2),
                    "target":     target,
                    "stop":       stop,
                    "confidence": round(confidence, 1),
                    "reasoning":  reasoning,
                    "source":     "TA Engine (direct yfinance)",
                },
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"  ✓ {ticker}: {action} @ ₹{price:.2f} | Conf: {confidence:.0f}% | Score: {score}")

        except Exception as e:
            logger.error(f"  ✗ Direct TA failed for {ticker}: {e}")

    return recommendations


# ─────────────────────────────────────────────────────────────────────────────
# Populate SQLite from yfinance (so multi-agent pipeline works on next run)
# ─────────────────────────────────────────────────────────────────────────────

def _seed_database(tickers: list):
    """Store latest OHLCV in SQLite so the full agent pipeline can process it."""
    try:
        from agents.data_collection import DataCollectionAgent
        agent = DataCollectionAgent()
        agent.initialize()
        agent.run(mode="update", subset=tickers)
        logger.info("✅ SQLite database seeded with fresh data")
    except Exception as e:
        logger.warning(f"Database seed skipped (non-fatal): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    run_mode    = os.environ.get("RUN_MODE", "post_market")
    tickers_env = os.environ.get("TICKERS", "RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS,BAJFINANCE.NS,AXISBANK.NS,WIPRO.NS,LT.NS,MARUTI.NS")
    tickers     = [t.strip() for t in tickers_env.split(",") if t.strip()]

    logger.info("━" * 50)
    logger.info(f"  CI Runner  |  Mode: {run_mode}  |  {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    logger.info(f"  Tickers: {', '.join(tickers)}")
    logger.info("━" * 50)

    os.makedirs("data", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    # ── Always write fresh index prices ──
    _export_market_snapshot()

    if run_mode == "pre_market":
        logger.info("Pre-market: seeding DB only.")
        _seed_database(tickers)
        _save_results([], run_mode, [])
        return

    # ── Phase 1: Direct TA recommendations (works from Day 1, no SQLite needed) ──
    logger.info("Phase 1: Building direct TA recommendations...")
    ta_recs = _direct_ta_recommendations(tickers)
    logger.info(f"  Direct TA produced {len(ta_recs)} recommendations")

    # ── Phase 2: Seed DB for future multi-agent runs ──
    logger.info("Phase 2: Seeding SQLite database...")
    _seed_database(tickers)

    # ── Phase 3: Try full multi-agent pipeline (may add more/override) ──
    multi_agent_recs = []
    try:
        logger.info("Phase 3: Running full multi-agent pipeline...")
        multi_agent_recs = _run_multi_agent_pipeline(tickers)
        logger.info(f"  Multi-agent produced {len(multi_agent_recs)} recommendations")
    except Exception as e:
        logger.warning(f"Multi-agent pipeline skipped (non-fatal): {e}")

    # ── Merge: prefer multi-agent results if available ──
    final_recs = multi_agent_recs if multi_agent_recs else ta_recs

    # ── Always save news headlines too ──
    headlines = _fetch_news_headlines()

    _save_results(final_recs, run_mode, headlines)
    logger.info("━" * 50)
    logger.info(f"  Done. {len(final_recs)} recommendations committed to repo.")
    logger.info("━" * 50)


def _run_multi_agent_pipeline(tickers: list) -> list:
    from agents.data_processing import DataProcessingAgent
    from agents.prediction import PredictionAgent
    from agents.news_intelligence import NewsIntelligenceAgent
    from agents.strategy import StrategyAgent
    from agents.risk_management import RiskManagementAgent
    from agents.recommendation import RecommendationAgent

    news_result    = NewsIntelligenceAgent().run() if True else {}
    sentiment_data = (news_result or {}).get("data", {})

    proc_agent  = DataProcessingAgent();   proc_agent.initialize()
    pred_agent  = PredictionAgent();       pred_agent.initialize()
    strat_agent = StrategyAgent();         strat_agent.initialize()
    risk_agent  = RiskManagementAgent();   risk_agent.initialize()
    rec_agent   = RecommendationAgent();   rec_agent.initialize()

    recommendations = []
    for ticker in tickers:
        try:
            proc = proc_agent.run(ticker=ticker)
            if not proc["success"] or proc["data"] is None:
                continue
            df  = proc["data"]["data"] if isinstance(proc["data"], dict) else proc["data"]
            pd  = pred_agent.run(df=df, ticker=ticker).get("data", {})
            sr  = strat_agent.run(df=df, ticker=ticker, prediction_data=pd, sentiment_data=sentiment_data)
            if not sr["success"]: continue
            rr  = risk_agent.run(strategy=sr["data"], current_portfolio_value=1_000_000)
            rd  = rr.get("data", {})
            if rd and rd.get("passed"):
                rr2 = rec_agent.run(risk_data=rd)
                if rr2["success"] and rr2["data"]:
                    recommendations.append({
                        "ticker": ticker, "result": rr2["data"],
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(f"  ✓ Multi-agent: {ticker}")
        except Exception as e:
            logger.warning(f"  Multi-agent skipped {ticker}: {e}")

    return recommendations


def _fetch_news_headlines() -> list:
    try:
        import feedparser
        feeds = {
            "Economic Times": "https://economictimes.indiatimes.com/markets/rss.cms",
            "Moneycontrol":   "https://www.moneycontrol.com/rss/latestnews.xml",
            "LiveMint":       "https://www.livemint.com/rss/markets",
        }
        headlines = []
        for source, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    headlines.append({
                        "source":   source,
                        "headline": entry.get("title", ""),
                        "time":     datetime.now().strftime("%H:%M"),
                        "label":    "NEUTRAL",
                        "score":    0,
                    })
            except Exception:
                pass
        logger.info(f"  Fetched {len(headlines)} news headlines")
        return headlines
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
        return []


def _save_results(recommendations: list, mode: str, headlines: list):
    output = {
        "run_mode":       mode,
        "run_at":         datetime.now().isoformat(),
        "count":          len(recommendations),
        "recommendations": recommendations,
        "headlines":       headlines,
    }
    path = "data/recommendations.json"
    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"✅ Saved {len(recommendations)} recommendations + {len(headlines)} headlines → {path}")


if __name__ == "__main__":
    main()
