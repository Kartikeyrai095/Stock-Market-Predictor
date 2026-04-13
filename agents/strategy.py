"""
Agent 7: Strategy
Generates trading strategies (Intraday, Swing, Options) utilizing data from
Processing, Prediction, and News agents.
"""

from agents.base_agent import BaseAgent
from config import OPTIONS_CONFIG
import pandas as pd
import numpy as np

class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__("Strategy")

    def initialize(self) -> bool:
        return True

    def execute(self, df: pd.DataFrame, ticker: str, prediction_data: dict, sentiment_data: dict, **kwargs) -> dict:
        """
        Synthesize technicals, ML predictions, and sentiment into a concrete trade strategy.
        """
        self.logger.info(f"Generating strategy for {ticker}")
        
        if df is None or df.empty:
            return {"success": False, "error": "No data available"}
            
        latest = df.iloc[-1]
        current_price = latest.get('Close', 0)
        
        if current_price == 0:
             return {"success": False, "error": "Invalid current price"}

        # Compile insights
        ml_eval = self._evaluate_prediction(prediction_data, current_price)
        ta_eval = self._evaluate_technicals(latest)
        sent_eval = self._evaluate_sentiment(sentiment_data)
        
        # Determine overall signal
        score = ml_eval["score"] + ta_eval["score"] + sent_eval["score"]
        
        action = "HOLD"
        if score >= 3:
            action = "BUY"
        elif score <= -3:
            action = "SELL"
            
        # Define Targets and Stops
        atr = latest.get('ATR', current_price * 0.02) # Fallback to 2% if missing
        
        if action == "BUY":
            entry = current_price
            stop_loss = entry - (1.5 * atr)
            target_1 = entry + (2.0 * atr)
            target_2 = entry + (3.5 * atr)
        elif action == "SELL":
            entry = current_price
            stop_loss = entry + (1.5 * atr)
            target_1 = entry - (2.0 * atr)
            target_2 = entry - (3.5 * atr)
        else: # HOLD
            entry = stop_loss = target_1 = target_2 = 0

        strategy = {
            "ticker": ticker,
            "strategy_type": "Swing", # Defaulting to Swing for daily data
            "action": action,
            "entry_price": float(entry),
            "target_price_1": float(target_1),
            "target_price_2": float(target_2),
            "stop_loss": float(stop_loss),
            "total_score": score,
            "components": {
                "ML": ml_eval,
                "TA": ta_eval,
                "Sentiment": sent_eval
            }
        }
        
        if action != "HOLD":
            self.logger.info(f"Generated {action} strategy for {ticker} at {entry:.2f}")
            
        return strategy

    def _evaluate_prediction(self, pred_data: dict, current_price: float) -> dict:
        """Score based on ML prediction: +2 Strong Buy, -2 Strong Sell"""
        score = 0
        reason = "Neutral"
        
        if pred_data and pred_data.get("predicted"):
            res = pred_data.get("results", {})
            ensemble = res.get("Ensemble")
            
            if ensemble:
                pct_diff = (ensemble / current_price) - 1
                if pct_diff > 0.05:
                    score = 2
                    reason = f"ML predicts >5% upside"
                elif pct_diff > 0.01:
                    score = 1
                    reason = "ML predicts slight upside"
                elif pct_diff < -0.05:
                    score = -2
                    reason = "ML predicts >5% downside"
                elif pct_diff < -0.01:
                    score = -1
                    reason = "ML predicts slight downside"

        return {"score": score, "reasoning": reason}

    def _evaluate_technicals(self, latest: pd.Series) -> dict:
        """Score based on TA: +2 Bullish, -2 Bearish"""
        score = 0
        reasons = []
        
        # EMA alignment
        if latest.get('EMA_9', 0) > latest.get('EMA_21', 0):
            score += 1
            reasons.append("EMA 9 > 21")
        elif latest.get('EMA_9', 0) < latest.get('EMA_21', 0):
            score -= 1
            
        # RSI
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            score += 1
            reasons.append("RSI Oversold")
        elif rsi > 70:
            score -= 1
            reasons.append("RSI Overbought")
            
        # MACD
        if latest.get('MACD', 0) > latest.get('MACD_signal', 0):
            score += 1
            reasons.append("MACD Bullish Cross")
        elif latest.get('MACD', 0) < latest.get('MACD_signal', 0):
            score -= 1
            
        return {"score": score, "reasoning": ", ".join(reasons) if reasons else "Neutral"}

    def _evaluate_sentiment(self, sentiment_data: dict) -> dict:
        """Score based on News: +2 Pos, -2 Neg"""
        score = 0
        reason = "Neutral"
        
        if sentiment_data and "aggregate_market_score" in sentiment_data:
            s_score = sentiment_data["aggregate_market_score"]
            if s_score > 0.5:
                score = 2
                reason = "Highly Positive News"
            elif s_score > 0.1:
                score = 1
                reason = "Positive News"
            elif s_score < -0.5:
                score = -2
                reason = "Highly Negative News"
            elif s_score < -0.1:
                score = -1
                reason = "Negative News"
                
        return {"score": score, "reasoning": reason}
