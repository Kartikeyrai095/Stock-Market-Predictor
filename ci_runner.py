"""
ci_runner.py — GitHub Actions Entry Point
A lightweight, CI-friendly version of the main pipeline.
Reads RUN_MODE and TICKERS from environment variables set by the workflow.
Exports final recommendations to a JSON file for artifact upload.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger

logger = get_logger("CI_Runner")

def _export_market_snapshot(tickers):
    """Write a quick market snapshot JSON so the dashboard overview cards update."""
    try:
        import yfinance as yf
        indices = {
            "^NSEI":    "NIFTY_50",
            "^BSESN":   "SENSEX",
            "^NSEBANK": "BANK_NIFTY",
        }
        snapshot_indices = {}
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                if len(hist) >= 2:
                    today = float(hist['Close'].iloc[-1])
                    prev  = float(hist['Close'].iloc[-2])
                    change = round((today - prev) / prev * 100, 2)
                    snapshot_indices[name] = {"price": round(today, 2), "change": change}
            except Exception:
                pass

        output = {
            "generated_at": datetime.now().isoformat(),
            "indices": snapshot_indices,
        }
        os.makedirs("data", exist_ok=True)
        with open("data/market_snapshot.json", "w") as f:
            json.dump(output, f, indent=2)
        logger.info("Market snapshot written to data/market_snapshot.json")
    except Exception as e:
        logger.warning(f"Could not write market snapshot: {e}")


def main():
    run_mode = os.environ.get("RUN_MODE", "post_market")
    tickers_env = os.environ.get("TICKERS", "RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS")
    tickers = [t.strip() for t in tickers_env.split(",") if t.strip()]

    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"  GitHub Actions CI Runner Starting")
    logger.info(f"  Mode      : {run_mode}")
    logger.info(f"  Tickers   : {tickers}")
    logger.info(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Ensure dirs exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    # ─── Always write a fresh market snapshot (for dashboard index cards) ───
    _export_market_snapshot(tickers)

    # Import agents (deferred to show cleaner log order)
    from agents.data_collection import DataCollectionAgent
    from agents.data_processing import DataProcessingAgent
    from agents.prediction import PredictionAgent
    from agents.news_intelligence import NewsIntelligenceAgent
    from agents.strategy import StrategyAgent
    from agents.risk_management import RiskManagementAgent
    from agents.recommendation import RecommendationAgent

    # ─── Phase 1: Always fetch latest data ───
    logger.info("Phase 1: Fetching market data...")
    data_agent = DataCollectionAgent()
    data_agent.initialize()
    data_agent.run(mode="update", subset=tickers)
    
    if run_mode == "pre_market":
        logger.info("Pre-market mode: Data fetch complete. Skipping analysis.")
        _save_results([], run_mode)
        return

    # ─── Phase 2: Full analysis (post-market) ───
    logger.info("Phase 2: Running full AI analysis pipeline...")
    news_agent = NewsIntelligenceAgent()
    news_agent.initialize()
    news_result = news_agent.run()
    sentiment_data = news_result.get("data", {})

    proc_agent = DataProcessingAgent()
    proc_agent.initialize()
    
    predict_agent = PredictionAgent()
    predict_agent.initialize()

    strat_agent = StrategyAgent()
    strat_agent.initialize()

    risk_agent = RiskManagementAgent()
    risk_agent.initialize()

    rec_agent = RecommendationAgent()
    rec_agent.initialize()

    recommendations = []

    for ticker in tickers:
        logger.info(f"  → Analyzing {ticker}...")
        try:
            proc_result = proc_agent.run(ticker=ticker)
            if not proc_result["success"] or proc_result["data"] is None:
                logger.warning(f"  ✗ Data processing failed for {ticker}. Skipping.")
                continue

            df = proc_result["data"]["data"] if isinstance(proc_result["data"], dict) else proc_result["data"]

            pred_result = predict_agent.run(df=df, ticker=ticker)
            pred_data = pred_result.get("data", {})

            strat_result = strat_agent.run(
                df=df, ticker=ticker,
                prediction_data=pred_data,
                sentiment_data=sentiment_data
            )

            if not strat_result["success"]:
                continue

            raw_strategy = strat_result["data"]
            risk_result = risk_agent.run(strategy=raw_strategy, current_portfolio_value=1_000_000)
            risk_data = risk_result.get("data", {})

            if risk_data and risk_data.get("passed"):
                rec_result = rec_agent.run(risk_data=risk_data)
                if rec_result["success"] and rec_result["data"]:
                    recommendations.append({
                        "ticker": ticker,
                        "result": rec_result["data"],
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(f"  ✓ Recommendation generated for {ticker}")
        except Exception as e:
            logger.error(f"  ✗ Error processing {ticker}: {e}")

    # ─── Phase 3: Save results ───
    _save_results(recommendations, run_mode)
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"  CI Run Complete. {len(recommendations)} recommendations generated.")
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def _save_results(recommendations: list, mode: str):
    """Write recommendations to JSON so GitHub Actions can upload as artifact."""
    output = {
        "run_mode": mode,
        "run_at": datetime.now().isoformat(),
        "count": len(recommendations),
        "recommendations": recommendations
    }
    output_path = "data/recommendations.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
