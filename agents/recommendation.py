"""
Agent 9: Recommendation
Takes the finalized risk-adjusted strategy and outputs the canonical recommendation.
Saves to database for frontend display.
"""

from agents.base_agent import BaseAgent
from database.db_manager import db
from database.models import TradeRecommendation

class RecommendationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Recommendation")
        self.session = None

    def initialize(self) -> bool:
        try:
            self.session = db.get_session()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Recommendation DB: {e}")
            return False

    def execute(self, risk_data: dict, **kwargs) -> dict:
        """
        Takes the output from RiskManagement. 
        If passed=True, saves the recommendation to the database.
        """
        if not self.session:
            self.initialize()
            
        if not risk_data.get("passed"):
            self.logger.info("Recommendation aborted: Strategy did not pass risk check.")
            return {"status": "rejected", "reason": risk_data.get("reason")}
            
        strategy = risk_data["strategy"]
        ticker = strategy["ticker"]
        
        self.logger.info(f"Generating final recommendation for {ticker}")
        
        try:
            # Construct reasoning string
            comps = strategy.get("components", {})
            ml = comps.get("ML", {}).get("reasoning", "")
            ta = comps.get("TA", {}).get("reasoning", "")
            news = comps.get("Sentiment", {}).get("reasoning", "")
            
            reasoning = f"ML: {ml} | TA: {ta} | News: {news} | R:R: {strategy.get('risk_reward_ratio')}"
            
            # Map total score back to a pseudo-confidence percentage for UI
            # Max score is roughly 6. Let 6 = 95%, 3 = 60%
            score = strategy.get("total_score", 3)
            confidence = min(max((score / 6.0) * 100, 50.0), 99.0)

            rec = TradeRecommendation(
                ticker=ticker,
                strategy_type=strategy.get("strategy_type", "Swing"),
                action=strategy["action"],
                entry_price=strategy["entry_price"],
                target_price_1=strategy["target_price_1"],
                target_price_2=strategy["target_price_2"],
                stop_loss=strategy["stop_loss"],
                confidence=confidence,
                reasoning=reasoning
            )
            
            self.session.add(rec)
            self.session.commit()
            
            self.logger.info(f"Saved {strategy['action']} recommendation for {ticker} to DB.")
            
            return {
                "status": "published",
                "recommendation_id": rec.id,
                "data": strategy
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save recommendation for {ticker}: {e}")
            self.session.rollback()
            return {"status": "error", "error": str(e)}

    def __del__(self):
        if self.session:
            self.session.close()
